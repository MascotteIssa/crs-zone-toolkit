"""Moteur d'analyse : identification CRS/famille, répartition, distorsion, décision.

Noyau pur (ARCHITECTURE §2/§3) : reçoit un RegionProfile et la grille injectés,
n'importe ni typer/rich ni regions/, ne lit aucun fichier de config, ne contient
aucun littéral EPSG québécois (TP-40). Contrats : SPEC §4, DATA_REFERENCE §1/§6.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import geopandas as gpd
import shapely
from pyproj import CRS, Proj

from crs_zone_toolkit.core import decoupage
from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.errors import (
    EmptyLayerError,
    InvalidGeometryError,
    MissingCrsError,
)
from crs_zone_toolkit.core.profile import RegionProfile
from crs_zone_toolkit.core.results import (
    SCHEMA_VERSION,
    AnalysisResult,
    Distorsion,
    Emprise,
    Recommandation,
    ZonePart,
)
from crs_zone_toolkit.core.targets import (
    fuseau_par_zone as _fuseau_par_zone,
)
from crs_zone_toolkit.core.targets import (
    lambert_epsg as _lambert_epsg,
)
from crs_zone_toolkit.core.targets import (
    libelle_crs as _libelle_crs,
)
from crs_zone_toolkit.core.targets import (
    target_family as _target_family,
)
from crs_zone_toolkit.core.targets import (
    zone_epsg as _zone_epsg,
)


def _family_index(profile: RegionProfile) -> dict[int, str]:
    """Index {code EPSG → famille} construit uniquement à partir du profil."""
    index: dict[int, str] = {}
    for famille, code in profile.geographiques.items():
        index[code] = famille
    for famille, code in profile.multi_zones.items():
        index[code] = famille
    for fuseau in profile.fuseaux:
        index[fuseau.epsg_csrs] = "csrs"
        if fuseau.epsg_nad83 is not None:
            index[fuseau.epsg_nad83] = "nad83"
        if fuseau.epsg_nad27 is not None:
            index[fuseau.epsg_nad27] = "nad27"
    return index


def _family_from_datum(crs: CRS) -> str:
    """Repli : déduit la famille du nom de datum pyproj (D-J2-4). 'autre' sinon."""
    nom = (crs.datum.name if crs.datum else "").lower()
    if "canadian spatial reference system" in nom or "csrs" in nom:
        return "csrs"
    if "north american datum 1983" in nom or "nad83" in nom:
        return "nad83"
    if "north american datum 1927" in nom or "nad27" in nom:
        return "nad27"
    if "world geodetic system 1984" in nom or "wgs 84" in nom or "wgs84" in nom:
        return "wgs84"
    return "autre"


def _identify(crs: CRS, profile: RegionProfile) -> tuple[int | None, str, str, str | None]:
    """(epsg, etiquette, famille, reconnu) — lookup profil puis repli pyproj."""
    epsg = crs.to_epsg()
    etiquette = crs.name
    reconnu: str | None = None
    if epsg is not None:
        for candidat in profile.reconnus:
            if epsg in candidat.codes:
                reconnu = candidat.etiquette
                break
    famille = _family_index(profile).get(epsg) if epsg is not None else None
    if famille is None:
        famille = _family_from_datum(crs)
    return epsg, etiquette, famille, reconnu


def _prepare_layer(
    layer: gpd.GeoDataFrame, assume_crs: str | int | None
) -> tuple[gpd.GeoDataFrame, bool, list[str]]:
    """Valide et prépare la couche avant analyse (SPEC §10). Lève les vraies erreurs."""
    if len(layer) == 0:
        raise EmptyLayerError(msg.COUCHE_VIDE)

    warnings: list[str] = []
    gdf = layer
    suppose = False
    if gdf.crs is None:
        if assume_crs is None:
            raise MissingCrsError(msg.crs_absent())
        gdf = gdf.set_crs(CRS.from_user_input(assume_crs))
        suppose = True
        warnings.append(msg.CRS_SUPPOSE)

    if not gdf.geometry.is_valid.all():
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.apply(shapely.make_valid)
        warnings.append(msg.MAKE_VALID_APPLIQUE)
        if not gdf.geometry.is_valid.all() or gdf.geometry.is_empty.any():
            raise InvalidGeometryError(msg.GEOM_IRREPARABLE)

    return gdf, suppose, warnings


def _geometry_kind(gdf: gpd.GeoDataFrame) -> str:
    """Type dominant : point / line / polygon (par effectif de géométries)."""
    familles = {
        "Point": "point",
        "MultiPoint": "point",
        "LineString": "line",
        "MultiLineString": "line",
        "Polygon": "polygon",
        "MultiPolygon": "polygon",
    }
    comptes: dict[str, int] = {}
    for geom_type in gdf.geometry.geom_type:
        kind = familles.get(geom_type, "polygon")
        comptes[kind] = comptes.get(kind, 0) + 1
    return max(comptes, key=lambda k: comptes[k])


def _boundary_parts(poly: Any) -> list[Any]:
    """Anneaux EXTÉRIEURS du contour, à l'exclusion de tout anneau intérieur (trou) :
    une seule partie pour un Polygon (même à trous), une par sous-polygone pour un
    MultiPolygon (DT-13, revue chantier A).

    `poly.boundary` inclurait les anneaux des trous éventuels (`MultiLineString`),
    mais l'intérieur d'un polygone ne peut jamais porter un extremum de longitude/
    latitude : leur allouer du budget d'échantillonnage serait pur gaspillage. On
    ne considère donc que `.exterior` de chaque sous-polygone.

    DT-09 : une `GeometryCollection` intruse (sortie d'intersection d'outils SIG
    amont, classée polygone par `_geometry_kind` faute de famille dédiée) n'a pas
    de `.exterior` propre — on descend dans ses membres surfaciques ; tout autre
    type non surfacique renvoie `[]` plutôt que de lever."""
    if poly.geom_type == "GeometryCollection":
        # DT-09 : une GC peut contenir n'importe quoi — on ne retient que les
        # membres surfaciques ; les autres n'ont pas de contour extérieur à offrir.
        parts: list[Any] = []
        for membre in poly.geoms:
            if membre.geom_type in ("Polygon", "MultiPolygon"):
                parts.extend(_boundary_parts(membre))
        return parts
    if poly.geom_type == "MultiPolygon":
        return [sous_poly.exterior for sous_poly in poly.geoms]
    if poly.geom_type == "Polygon":
        return [poly.exterior]
    return []  # type non surfacique dans une couche à majorité polygones


def _contour_points(poly: Any, budget: int) -> list[tuple[float, float]]:
    """`budget` points à fractions régulières du contour de `poly` (DT-13).

    Le contour porte les extrêmes de l'emprise (longitude pour MTM, latitude pour
    Lambert), là où vit le max de distorsion — contrairement à l'intérieur. Pour un
    MultiPolygon, le budget est réparti entre les parties **au prorata de leur
    longueur** (répartition la plus simple qui reste déterministe ; une pondération
    par surface n'apporterait rien au critère, qui est un extremum de longitude/
    latitude, pas de surface).
    """
    parts = _boundary_parts(poly)
    longueurs = [float(p.length) for p in parts]
    total = sum(longueurs)
    if total <= 0:
        return []
    comptes: list[int] = []
    alloue = 0
    for i, longueur in enumerate(longueurs):
        if i == len(longueurs) - 1:
            compte = budget - alloue  # dernière partie : récupère le reliquat d'arrondi
        else:
            compte = round(budget * longueur / total)
            alloue += compte
        # `max(compte, 0)` : si les arrondis des parties précédentes ont cumulé au-delà
        # du budget (`alloue > budget`), le reliquat de la dernière partie est négatif ;
        # on l'écrête à 0 plutôt que de lever. Dans ce cas rare, la somme réelle des
        # comptes est strictement inférieure à `budget` (quelques points de contour en
        # moins, jamais un plantage) — accepté, la décimation globale à `n` en aval
        # absorbe de toute façon les écarts de effectif.
        comptes.append(max(compte, 0))
    points: list[tuple[float, float]] = []
    for part, compte in zip(parts, comptes, strict=True):
        for i in range(compte):
            p = part.interpolate(i / compte, normalized=True)
            points.append((p.x, p.y))
    return points


def _decimer(points: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """Ramène l'échantillon à `n` points en conservant **les deux extrémités** (DT-24).

    L'ancienne formule `points[int(i * pas)]` avec `pas = len / n` n'atteignait
    jamais le dernier indice : sur 300 points ramenés à 200, elle s'arrêtait à
    298. Or les extrémités sont exactement ce qu'une mesure de min/max ne peut
    pas perdre — sur un contour de polygone, ce sont les points les plus
    éloignés de la méridienne centrale, donc les plus déformés.

    `round(i * (len - 1) / (n - 1))` place le premier point sur l'indice 0 et le
    dernier sur `len - 1`, en pas réguliers. Déterministe (SPEC §4.2.4).
    """
    if len(points) <= n:
        return points
    if n == 1:
        return [points[0]]
    pas = (len(points) - 1) / (n - 1)
    return [points[round(i * pas)] for i in range(n)]


def _points_dans_profil(
    points: list[tuple[float, float]], grid: gpd.GeoDataFrame
) -> list[tuple[float, float]]:
    """Ne garde que les points tombant dans un fuseau du profil (DT-24).

    Même prédicat (`within`) et même grille que `_repartition` : ce qui compte
    comme « hors profil » dans la couverture compte comme hors profil dans la
    mesure. Sans quoi l'outil annonce « aucune recommandation pour cette part »,
    puis juge la projection **sur** cette part (observation N12).
    """
    if not points:
        return points
    pts = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([p[0] for p in points], [p[1] for p in points]),
        crs=grid.crs,
    )
    joint = gpd.sjoin(pts, grid[["geometry"]], predicate="within", how="left")
    # sjoin peut dupliquer une ligne si un point tombe dans deux cellules
    # (méridien-frontière, DT-09) : on dédoublonne par indice source.
    dedans = sorted(set(joint.dropna(subset=["index_right"]).index))
    return [points[i] for i in dedans]


def _sample_lonlat(
    gdf_wgs84: gpd.GeoDataFrame, kind: str, n: int, *, grid: gpd.GeoDataFrame
) -> tuple[list[float], list[float]]:
    """Points d'échantillon (lon, lat) déterministes, plafonnés à n (SPEC §4.2.4).

    Polygones (DT-13) : point représentatif conservé **+** points du contour, à
    fractions régulières de la longueur (même famille de technique que les lignes,
    donc déterministe). Budget de contour par entité = `max(2, n // n_entités)`,
    en plus du représentatif ; la décimation globale à `n` reste le mécanisme final.

    **Les points hors profil sont écartés avant la décimation** (DT-24) : le
    budget `n` se dépense sur des points qui comptent. Si l'exclusion ne laisse
    **rien** — couche 100 % hors profil — l'échantillon brut est conservé :
    `_distortion` fait `min()`/`max()` sur les ppm et planterait sur une liste
    vide, et le verdict est de toute façon « aucune » (aucun fuseau touché), donc
    les chiffres sont lus dans un écran qui déclare déjà le hors-profil total.
    """
    geoms = gdf_wgs84.geometry
    points = []
    if kind == "point":
        # representative_point() renvoie le point lui-même pour un Point, et un
        # point intérieur valide pour un MultiPoint (qui n'a ni .x ni .y) (I1).
        points = [(p.x, p.y) for p in (g.representative_point() for g in geoms)]
    elif kind == "line":
        for ligne in geoms:
            if ligne.geom_type in ("LineString", "MultiLineString"):
                for frac in (0.0, 0.5, 1.0):
                    p = ligne.interpolate(frac, normalized=True)
                    points.append((p.x, p.y))
            else:  # GC ou autre intrus : point représentatif, jamais de plantage (DT-09)
                p = ligne.representative_point()
                points.append((p.x, p.y))
    else:
        n_entites = len(geoms)
        budget = max(2, n // max(n_entites, 1))
        for poly in geoms:
            rep = poly.representative_point()
            points.append((rep.x, rep.y))
            points.extend(_contour_points(poly, budget))
    points = _points_dans_profil(points, grid) or points
    points = _decimer(points, n)
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return lons, lats


def _repartition(
    gdf: gpd.GeoDataFrame, grid: gpd.GeoDataFrame, kind: str, measure_crs: int
) -> tuple[list[tuple[int, float]], float]:
    """Part par fuseau sur la grandeur dominante ; renvoie (zones triées, hors_profil).

    Données et grille sont reprojetées dans `measure_crs` (projection métrique du
    profil) avant toute mesure de longueur/surface : les parts ne subissent pas le
    biais des degrés WGS84 (supersède la simplification D-J2-6).
    """
    data = gdf.to_crs(measure_crs)
    cells = grid.to_crs(measure_crs)
    parts: dict[int, float] = {}

    if kind == "point":
        total = float(len(data))
        joint = gpd.sjoin(
            data[["geometry"]], cells[["zone", "geometry"]], predicate="within", how="left"
        )
        for zone, groupe in joint.dropna(subset=["zone"]).groupby("zone"):
            parts[int(zone)] = len(groupe) / total
    else:
        # geopandas n'expose pas de stubs typés : les géométries traversent en Any.
        # Les lambdas nues seraient des fonctions non annotées ; on les nomme et
        # on les annote explicitement pour satisfaire mypy strict (no-untyped-call).
        def _mesure_ligne(g: Any, cell: Any) -> float:
            return float(g.intersection(cell).length)

        def _mesure_polygone(g: Any, cell: Any) -> float:
            return float(g.intersection(cell).area)

        mesure: Callable[[Any, Any], float] = _mesure_ligne if kind == "line" else _mesure_polygone
        total = float(data.geometry.length.sum() if kind == "line" else data.geometry.area.sum())
        for _, cellule in cells.iterrows():
            m = sum(mesure(g, cellule.geometry) for g in data.geometry)
            if m > 0:
                parts[int(cellule.zone)] = m / total

    zones = sorted(parts.items(), key=lambda item: item[1], reverse=True)
    hors = max(0.0, 1.0 - sum(parts.values()))
    return zones, hors


def _distortion(lons: list[float], lats: list[float], epsg: int, libelle: str) -> Distorsion:
    """Facteur d'échelle linéaire (meridional_scale) en ppm sur l'échantillon."""
    facteurs = Proj(CRS.from_epsg(epsg)).get_factors(lons, lats)
    # Le stub pyproj type Factors.meridional_scale en `float` scalaire (cas non
    # générique), mais get_factors() renvoie ici une séquence car lons/lats sont
    # des listes (cf. docstring get_factors : "list" est un type d'entrée accepté,
    # la sortie a la même forme). cast() reflète le comportement réel documenté.
    echelles = cast("list[float]", facteurs.meridional_scale)
    ppm = [(k - 1.0) * 1e6 for k in echelles]
    return Distorsion(
        libelle=libelle,
        epsg=epsg,
        min_ppm=min(ppm),
        moy_ppm=sum(ppm) / len(ppm),
        max_ppm=max(ppm),
    )


def _max_abs_ppm(distorsion: Distorsion) -> float:
    """Distorsion maximale en valeur absolue (critère de décision SPEC §4.3)."""
    return max(abs(distorsion.min_ppm), abs(distorsion.max_ppm))


def analyze(
    layer: gpd.GeoDataFrame,
    name: str,
    *,
    profile: RegionProfile,
    grid: gpd.GeoDataFrame,
    assume_crs: str | int | None = None,
    n_samples: int | None = None,
) -> AnalysisResult:
    """Analyse une couche déjà chargée (noyau pur) → AnalysisResult (SPEC §4)."""
    gdf, suppose, warnings = _prepare_layer(layer, assume_crs)
    crs = gdf.crs
    epsg, etiquette, famille, reconnu = _identify(crs, profile)
    if reconnu is not None:
        warnings.append(msg.note_reconnu(reconnu))

    n = n_samples if n_samples is not None else profile.seuils.n_echantillons
    kind = _geometry_kind(gdf)
    data_wgs84 = gdf.to_crs(grid.crs)
    # Mesure des parts dans une projection métrique du profil (Lambert provincial,
    # datum-indépendant pour des parts relatives) — évite le biais des degrés (D-J2-6 superseded).
    measure_crs = profile.multi_zones["csrs"]
    zones_brut, hors = _repartition(gdf, grid, kind, measure_crs)
    target = _target_family(famille)

    zones = tuple(
        ZonePart(zone=zone, epsg=_zone_epsg(_fuseau_par_zone(profile, zone), target), part=part)
        for zone, part in zones_brut
    )

    lons, lats = _sample_lonlat(data_wgs84, kind, n, grid=grid)
    lambert_epsg = _lambert_epsg(profile, target)
    # DT-20 n°1 : le libellé du CRS multi-zones est une donnée régionale (profil) ;
    # le nom brut pyproj ne sert que de repli (TP-41 : profils sans la donnée).
    libelle_lambert = profile.etiquette_multi_zones or _libelle_crs(lambert_epsg)
    distorsions: list[Distorsion] = []
    if zones:
        dom_epsg = zones[0].epsg
        # DT-20 (1) : « (tout) » dit que la mesure porte sur TOUTE la couche, y
        # compris hors de ce fuseau — l'information que N12 a montrée manquante.
        libelle_dom = msg.libelle_candidat_fuseau(zones[0].zone, multi_fuseaux=len(zones) > 1)
        distorsions.append(_distortion(lons, lats, dom_epsg, libelle_dom))
    distorsions.append(_distortion(lons, lats, lambert_epsg, libelle_lambert))

    warnings.extend(_datum_warnings(famille))
    # DT-12 : le seuil est celui de l'affichage (round à la % près) — une écharde
    # infime liée à la simplification du profil (0,005°) ne doit pas produire un
    # avertissement « 0 % hors profil » absurde. `part_hors_profil` reste exact.
    if round(hors * 100) >= 1:
        warnings.append(msg.hors_profil(hors))

    # DT-25 : le compte annoncé doit être celui des FICHIERS, pas des fuseaux
    # traversés. Calculé seulement quand un découpage peut être offert (≥ 2
    # fuseaux) — l'affectation majoritaire est en O(entités × cellules).
    zones_sorties = decoupage.zones_majoritaires(gdf, grid, measure_crs) if len(zones) > 1 else []
    recommandation = _decide(
        zones, distorsions, profile, target, lambert_epsg, libelle_lambert, zones_sorties
    )

    minx, miny, maxx, maxy = (float(v) for v in data_wgs84.total_bounds)
    return AnalysisResult(
        schema_version=SCHEMA_VERSION,
        couche=name,
        crs_entree={"epsg": epsg, "etiquette": etiquette, "suppose": suppose, "reconnu": reconnu},
        famille=famille,
        type_geometrie=kind,
        emprise=Emprise(minx, miny, maxx, maxy),
        zones_traversees=zones,
        part_hors_profil=hors,
        distorsions=tuple(distorsions),
        recommandation=recommandation,
        avertissements=tuple(warnings),
        parametres={
            "region": profile.id,
            "n_echantillons": n,
            "n_echantillons_effectif": len(lons),
            "part_dominante_min": profile.seuils.part_dominante_min,
            "distorsion_max_ppm": profile.seuils.distorsion_max_ppm,
        },
    )


def _datum_warnings(famille: str) -> list[str]:
    """Avertissements de datum — réservés à ce qui présente un risque (DT-26).

    NAD27 est le seul cas restant : la cible change de famille **et** exige une
    grille NTv2 à l'exécution, ce que la ligne « Datum : » ne dit pas à elle
    seule.

    La **préservation** (NAD83, CSRS) n'est plus un avertissement : c'est le cas
    le moins risqué, et l'ancien message ne faisait que répéter la ligne
    « Datum : ». Le **changement** de famille (WGS 84, datum non identifié) n'en
    reçoit pas non plus : il est désormais marqué d'un ⚠ sur la ligne « Datum :»
    elle-même, là où le fait est énoncé — sans quoi le marqueur et le texte
    diraient deux fois la même chose.
    """
    if famille == "nad27":
        return [msg.NAD27_NTV2]
    return []


def _decide(
    zones: tuple[ZonePart, ...],
    distorsions: list[Distorsion],
    profile: RegionProfile,
    target: str,
    lambert_epsg: int,
    libelle_lambert: str,
    zones_sorties: list[int],
) -> Recommandation:
    """Arbre de décision SPEC §4.3 — règle « distorsion d'abord » (calibrage J6/§5).

    Un seul fuseau → ce fuseau. Sinon, on recommande la **projection unique la
    moins déformée** entre le fuseau dominant et le Québec Lambert (le fuseau
    l'emporte à égalité : un fichier local vaut mieux que le Lambert provincial).
    Le découpage par fuseau est toujours offert en alternative dès qu'il y a
    plusieurs fuseaux. La tolérance ``distorsion_max_ppm`` ne gate plus le choix :
    elle qualifie le motif (sous tolérance, ou « meilleure mais au-delà → le
    découpage garde chaque morceau sous le seuil »). ``part_dominante_min`` n'est
    plus consulté (conservé au profil pour transparence — voir DT-16).

    ``zones_sorties`` : les fuseaux qui recevraient **au moins une entité** par
    affectation majoritaire — donc le nombre de **fichiers** que produirait le
    découpage. Distinct des fuseaux **traversés** (``zones``), qui peuvent être
    plus nombreux : une entité à cheval ne va que dans un fichier (DT-25).
    """
    if not zones:
        # 100 % hors profil : aucun fuseau touché, aucune recommandation possible
        # (garde anti-IndexError).
        return Recommandation("aucune", 0, "", "hors_profil", msg.motif_hors_profil_total(), ())

    dominant = zones[0]

    if len(zones) == 1:
        return Recommandation(
            "zone",
            dominant.epsg,
            msg.libelle_fuseau(dominant.zone),
            "mono_zone",
            msg.motif_mono_zone(dominant.zone),
            (),
        )

    # N20/N23 : le découpage n'est offert — ni promis — que s'il produit
    # PLUSIEURS fichiers. À une sortie, il est identique à une reprojection vers
    # le fuseau majoritaire, et le motif qui annonçait qu'il « garde chaque
    # morceau sous le seuil » énonçait une chose fausse.
    decoupage_utile = len(zones_sorties) > 1
    split = ({"action": "split", "zones": zones_sorties},) if decoupage_utile else ()
    seuil = profile.seuils.distorsion_max_ppm
    dom_ppm = _max_abs_ppm(distorsions[0])  # le fuseau dominant est le 1er candidat
    lam_distorsion = next(d for d in distorsions if d.epsg == lambert_epsg)
    lam_ppm = _max_abs_ppm(lam_distorsion)

    if dom_ppm <= lam_ppm:
        if dom_ppm <= seuil:
            return Recommandation(
                "zone",
                dominant.epsg,
                msg.libelle_fuseau(dominant.zone),
                "zone_dominante",
                msg.motif_zone_dominante(dominant.zone, dominant.part, dom_ppm),
                split,
            )
        return Recommandation(
            "zone",
            dominant.epsg,
            msg.libelle_fuseau(dominant.zone),
            "zone_moins_deformee",
            msg.motif_zone_moins_deformee(
                dominant.zone, dom_ppm, seuil, decoupage_utile=decoupage_utile
            ),
            split,
        )
    return Recommandation(
        "lambert",
        lambert_epsg,
        libelle_lambert,
        "lambert_moins_deforme",
        msg.motif_lambert_moins_deforme(
            dominant.zone, dom_ppm, lam_ppm, decoupage_utile=decoupage_utile
        ),
        split,
    )
