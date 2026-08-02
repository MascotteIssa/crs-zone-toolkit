"""DT-13/DT-12 — échantillonnage des polygones par le contour, seuil d'affichage
« hors profil » à 1 % (DT-13, DT-12).

Aucune grille PROJ requise (qc_profile/qc_grid suffisent, pas de transformation
de datum). Déterministe : pas de random dans le chemin testé.
"""

import json

import geopandas as gpd
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

from crs_zone_toolkit.core.analysis import _boundary_parts, analyze


def _json(layer: gpd.GeoDataFrame, profile, grid, **kw) -> dict:
    return json.loads(analyze(layer, "essai", profile=profile, grid=grid, **kw).to_json())


def _points(coords: list[tuple[float, float]], crs: int = 4326) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in coords], crs=crs)


# ── DT-13 : échantillonnage des polygones par le contour ──────────────────


def test_dt13_polygone_large_distorsion_captee_aux_bords(
    tp03_polygones_quatre_fuseaux, qc_profile, qc_grid
) -> None:
    """Un seul polygone (boîte lon -78,5°→-70°) : le point représentatif seul
    (avant correctif) donne min = moy = max (~-60 ppm partout, mesuré au centre).
    Après correctif (contour densifié), le candidat MTM dominant doit montrer
    une distorsion très différente entre les bords (~3-4° du méridien central)
    et le centre : max_ppm strictement > min_ppm, et l'extrême en valeur absolue
    de l'ordre du millier de ppm.
    """
    data = _json(tp03_polygones_quatre_fuseaux, qc_profile, qc_grid)
    dominant_epsg = data["zones_traversees"][0]["epsg"]
    distorsion = data["distorsion"][str(dominant_epsg)]
    assert distorsion["max_ppm"] > distorsion["min_ppm"]
    assert max(abs(distorsion["min_ppm"]), abs(distorsion["max_ppm"])) > 1000


def test_boundary_parts_polygone_a_trou_ignore_le_trou() -> None:
    """Un Polygon À TROU ne doit produire qu'UNE seule partie : l'anneau extérieur.

    Avant correctif, `.boundary` d'un Polygon à trou renvoie un MultiLineString
    (anneau extérieur + anneau du trou) : `_boundary_parts` renvoyait alors 2
    parties et allouait du budget d'échantillonnage au trou, qui ne peut jamais
    porter un extremum de longitude/latitude (revue chantier A)."""
    exterieur = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
    trou = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0), (4.0, 4.0)]
    poly = Polygon(exterieur, holes=[trou])
    parts = _boundary_parts(poly)
    assert len(parts) == 1
    assert parts[0].equals(LineString(poly.exterior))


def test_boundary_parts_multipolygon_deux_parties_trou_ignore() -> None:
    """MultiPolygon de 2 sous-polygones (dont un à trou) → exactement 2 parties,
    les 2 anneaux extérieurs (le trou du second sous-polygone est ignoré)."""
    p1 = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)])
    p2 = Polygon(
        [(10.0, 10.0), (12.0, 10.0), (12.0, 12.0), (10.0, 12.0), (10.0, 10.0)],
        holes=[[(10.5, 10.5), (11.5, 10.5), (11.5, 11.5), (10.5, 11.5), (10.5, 10.5)]],
    )
    multi = MultiPolygon([p1, p2])
    parts = _boundary_parts(multi)
    assert len(parts) == 2
    assert parts[0].equals(LineString(p1.exterior))
    assert parts[1].equals(LineString(p2.exterior))


def test_dt13_multipolygon_deux_boites_capture_les_deux_extremes(qc_profile, qc_grid) -> None:
    """MultiPolygon de 2 boîtes distantes (lon ~-78,2° et ~-70,6°, lat 46,8-47,2,
    dans l'emprise du Québec) : le candidat MTM dominant doit capturer les deux
    extrêmes de longitude (contour de chaque sous-polygone échantillonné, DT-13).

    Doit rester vrai avant ET après le correctif « anneaux extérieurs seulement »
    (revue chantier A) : ni sous-polygone n'a de trou ici, le correctif ne retire
    donc rien à ce cas — seulement aux anneaux de trous, absents ici."""
    boite_ouest = box(-78.3, 46.8, -78.1, 47.2)
    boite_est = box(-70.7, 46.8, -70.5, 47.2)
    multi = MultiPolygon([boite_ouest, boite_est])
    layer = gpd.GeoDataFrame(geometry=[multi], crs=4326)
    data = _json(layer, qc_profile, qc_grid)
    dominant_epsg = data["zones_traversees"][0]["epsg"]
    distorsion = data["distorsion"][str(dominant_epsg)]
    assert distorsion["max_ppm"] != distorsion["min_ppm"]
    assert max(abs(distorsion["min_ppm"]), abs(distorsion["max_ppm"])) > 1000


def test_n_echantillons_effectif_present_et_coherent(
    tp03_polygones_quatre_fuseaux, qc_profile, qc_grid
) -> None:
    data = _json(tp03_polygones_quatre_fuseaux, qc_profile, qc_grid)
    n_effectif = data["parametres"]["n_echantillons_effectif"]
    n_entites = len(tp03_polygones_quatre_fuseaux)
    assert n_effectif >= n_entites
    assert n_effectif <= data["parametres"]["n_echantillons"]


def test_n_echantillons_effectif_points_egal_effectif(qc_profile, qc_grid) -> None:
    """Pour des points, chaque entité est un échantillon (SPEC §4.2.4) : l'effectif
    est le nombre d'entités tant qu'il ne dépasse pas le plafond `n_echantillons`.
    """
    pts = _points([(-71.9, 45.4), (-71.7, 45.5), (-71.8, 45.45)])
    data = _json(pts, qc_profile, qc_grid)
    assert data["parametres"]["n_echantillons_effectif"] == 3


# ── DT-12 : avertissement « hors profil » à partir de 1 % ─────────────────


def test_dt12_hors_profil_sous_le_pourcent_pas_davertissement(qc_profile, qc_grid) -> None:
    """1 point sur 250 hors profil (0,4 %) : la part reste exacte, mais l'écharde
    est trop fine pour déclencher l'avertissement (arrondi < 1 %).
    """
    quebec = [(-73.5 + i * 0.0001, 46.0 + i * 0.0001) for i in range(249)]
    winnipeg = [(-97.15, 49.90)]
    data = _json(_points(quebec + winnipeg), qc_profile, qc_grid)
    assert data["part_hors_profil"] > 0.0
    assert not any("hors du profil" in a for a in data["avertissements"])


def test_dt12_hors_profil_deux_pourcent_avertissement_present(qc_profile, qc_grid) -> None:
    """1 point sur 50 hors profil (2 %) : l'avertissement doit apparaître."""
    quebec = [(-73.5 + i * 0.0005, 46.0 + i * 0.0005) for i in range(49)]
    winnipeg = [(-97.15, 49.90)]
    data = _json(_points(quebec + winnipeg), qc_profile, qc_grid)
    assert data["part_hors_profil"] > 0.0
    assert any("hors du profil" in a for a in data["avertissements"])


def test_dt12_hors_profil_total_comportement_inchange(
    hors_profil_total_points, qc_profile, qc_grid
) -> None:
    """100 % hors profil (`hors_profil_total_points`, déjà couvert par
    `test_guard_hors_profil_total_ne_plante_pas`) : le seuil d'affichage à 1 %
    ne change rien à ce cas — la part est loin au-dessus, l'avertissement reste
    émis, `action = aucune` inchangée."""
    data = _json(hors_profil_total_points, qc_profile, qc_grid)
    assert data["part_hors_profil"] == 1.0
    assert data["recommandation"]["action"] == "aucune"
    assert any("hors du profil" in a for a in data["avertissements"])


# ── DT-24 — l'assiette de mesure, et la décimation qui décide ──────────────
#
# Observation N12 du test manuel : `_sample_lonlat` recevait la couche entière.
# Seule la *répartition* écartait le hors-profil, pas la mesure de distorsion —
# l'outil annonçait « aucune recommandation pour cette part », puis jugeait la
# projection SUR cette part. Effet mesuré sur le terrain : même grappe
# québécoise, MTM 8 à +263 ppm « ⚠ hors seuil » avec 100 points (le point
# d'Ottawa retenu), +25 ppm sans marqueur avec 300 (Ottawa décimé). Le marqueur
# dépendait donc d'un aléa d'échantillonnage.


def _grappe_quebec(n: int = 20) -> list[tuple[float, float]]:
    """Points serrés autour du méridien central du fuseau 8 (−73,5°)."""
    return [(-73.55 + i * 0.01, 45.50 + i * 0.005) for i in range(n)]


ONTARIO = (-79.40, 43.66)  # Toronto — hors de la limite du Québec


def test_dt24_le_point_hors_profil_ne_pese_plus_sur_la_distorsion(qc_profile, qc_grid) -> None:
    """Reproduction de N12 : un intrus hors profil ne doit plus déplacer les ppm."""
    sans = _json(_points(_grappe_quebec()), qc_profile, qc_grid)
    avec = _json(_points([*_grappe_quebec(), ONTARIO]), qc_profile, qc_grid)

    def maxi(doc: dict) -> float:
        return max(abs(d["max_ppm"]) for d in doc["distorsion"].values())

    assert maxi(avec) == maxi(sans), (
        "l'outil annonce « aucune recommandation pour cette part » puis "
        "juge la projection sur cette part"
    )


def test_dt24_le_hors_profil_reste_compte_dans_la_repartition(qc_profile, qc_grid) -> None:
    """Contre-épreuve : l'exclusion touche la MESURE, jamais la couverture.

    Sans elle, on pourrait « corriger » en écartant le hors-profil partout, ce
    qui ferait disparaître l'avertissement qui informe l'utilisateur.
    """
    doc = _json(_points([*_grappe_quebec(), ONTARIO]), qc_profile, qc_grid)

    assert doc["part_hors_profil"] > 0.0
    assert any("hors du profil" in a for a in doc["avertissements"])


def test_dt24_cent_pour_cent_hors_profil_mesure_quand_meme(qc_profile, qc_grid) -> None:
    """Garde : si l'exclusion ne laisse rien, la mesure retombe sur l'échantillon brut.

    `_distortion` fait `min()`/`max()` sur la liste des ppm — une liste vide la
    ferait planter. Le verdict reste « aucune » (aucun fuseau touché), donc les
    chiffres sont lus dans un écran qui déclare déjà le hors-profil total.
    """
    doc = _json(_points([ONTARIO, (-79.41, 43.67), (-79.42, 43.68)]), qc_profile, qc_grid)

    assert doc["part_hors_profil"] == 1.0
    assert doc["recommandation"]["action"] == "aucune"
    assert doc["distorsion"], "aucun plantage, et le tableau reste informatif"


def test_dt24_decimation_retient_les_deux_extremites() -> None:
    """N12 (b) : `points[int(i * pas)]` ne retenait jamais l'indice 299 sur 300.

    Les extrémités sont précisément ce qu'une mesure de min/max ne peut pas se
    permettre de perdre : sur un contour, ce sont les points les plus éloignés
    de la méridienne centrale.
    """
    from crs_zone_toolkit.core.analysis import _decimer

    source = [(float(i), 0.0) for i in range(300)]
    retenus = _decimer(source, 200)

    assert len(retenus) == 200
    assert retenus[0] == source[0]
    assert retenus[-1] == source[-1], "l'ancienne formule s'arrêtait à l'indice 298"
    assert retenus == sorted(retenus), "l'ordre de la source est conservé"


def test_dt24_decimation_ne_touche_pas_un_echantillon_deja_sous_le_plafond() -> None:
    from crs_zone_toolkit.core.analysis import _decimer

    source = [(float(i), 0.0) for i in range(5)]
    assert _decimer(source, 200) == source
