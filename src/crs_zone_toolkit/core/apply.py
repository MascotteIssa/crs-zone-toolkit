"""Exécution des décisions : reprojection, découpage par affectation majoritaire, journal.

Noyau (ARCHITECTURE §2/§3) : reçoit profil+grille+AnalysisResult injectés, n'importe
ni typer/rich ni regions/. Il ÉCRIT des fichiers (sorties + journal), c'est son rôle.
Contrats : SPEC §5/§9, DATA_REFERENCE §6.1. Aucun EPSG québécois en dur (TP-40).
"""

from __future__ import annotations

import json
import warnings
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
from pyproj import CRS
from pyproj.transformer import TransformerGroup

import crs_zone_toolkit
from crs_zone_toolkit.core import decoupage
from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.errors import OutputExistsError, TransformUnavailableError
from crs_zone_toolkit.core.profile import RegionProfile
from crs_zone_toolkit.core.results import AnalysisResult, ApplyResult, Decision, FichierProduit
from crs_zone_toolkit.core.targets import (
    fuseau_par_zone,
    lambert_epsg,
    target_family,
    zone_epsg,
)

# DT-19 : pilote ET extension dans la même table — elles ne peuvent plus diverger.
_FORMATS: dict[str, tuple[str, str]] = {
    "geojson": ("GeoJSON", "geojson"),
    "gpkg": ("GPKG", "gpkg"),
    "shp": ("ESRI Shapefile", "shp"),
}
FORMATS_SORTIE: tuple[str, ...] = tuple(sorted(_FORMATS))
"""Formats d'écriture acceptés par `apply` — source de vérité unique (DT-19).

La CLI valide en amont à partir de cette constante ; le noyau garde sa propre
vérification (DT-06) car l'API publique est appelable sans passer par la CLI.
"""


def _grilles_manquantes(groupe: TransformerGroup) -> tuple[str, ...]:
    """Grilles PROJ manquantes de l'opération indisponible la MIEUX classée.

    `unavailable_operations` est trié par pertinence : seule la première est
    celle que PROJ retiendrait si sa grille existait — c'est donc la seule
    actionnable. Balayer tout le groupe listerait une dizaine de grilles sans
    rapport (NAD27, réseaux américains…) et noierait le conseil.

    Défensif : jamais d'exception ici, au pire un tuple vide que les messages
    savent afficher.
    """
    try:
        indisponibles = groupe.unavailable_operations
        if not indisponibles:
            return ()
        return tuple(grille.short_name for grille in indisponibles[0].grids if not grille.available)
    except AttributeError:
        return ()


def _exige_transformation_exacte(
    famille_source: str, famille_cible: str, familles_obligatoires: tuple[str, ...]
) -> bool:
    """Vrai si la transformation exige une grille exacte (DT-01, DATA_REFERENCE §1.5).

    Les familles « à risque » sont déclarées par le PROFIL (jamais en dur ici,
    TP-40) : ce sont celles dont l'écart rend une approximation « ballpark »
    inacceptable — au Québec, NAD27 (dizaines de mètres). Entre familles
    modernes, l'écart mesuré est nul à décimétrique : le repli est accepté,
    mais toujours avertissable et journalisé (DATA_REFERENCE §6.1).
    """
    return famille_source in familles_obligatoires or famille_cible in familles_obligatoires


def _reproject(
    gdf: gpd.GeoDataFrame, dst_epsg: int, *, exige_grille: bool
) -> tuple[gpd.GeoDataFrame, str, list[str]]:
    """Reprojette vers dst_epsg ; capture le pipeline PROJ ; arbitre le repli « ballpark ».

    Quand PROJ ne peut offrir que du « ballpark » pour un changement de datum
    (grille absente), deux issues (DATA_REFERENCE §6.1 : « refuse OU avertit ») :

    - `exige_grille` vrai — la famille source ou cible est déclarée à risque par
      le profil (NAD27 au Québec : dizaines de mètres) → refus.
    - `exige_grille` faux — familles modernes entre elles, y compris les
      réalisations d'une même famille (le Lambert 6622 est en CSRS **v2** alors
      que 4617 est en CSRS générique) : écart mesuré nul à décimétrique → on
      accepte, mais on AVERTIT ; l'avertissement remonte au journal (DT-01).

    Note d'implémentation : la version de pyproj installée (3.7.2) n'expose pas
    l'attribut Transformer.is_ballpark. Le repli documenté est utilisé :
    `not groupe.best_available` (vrai quand la meilleure transformation
    nécessite une grille absente).
    """
    src = gdf.crs
    dst = CRS.from_epsg(dst_epsg)
    with warnings.catch_warnings():
        # pyproj avertit lui-même « Best transformation is not available… ».
        # On INSPECTE cette condition juste en dessous (best_available) et on la
        # restitue par nos propres messages, en français et journalisés : relayer
        # en plus l'avertissement brut ne ferait que polluer stderr.
        warnings.filterwarnings("ignore", category=UserWarning, module="pyproj")
        groupe = TransformerGroup(src, dst, always_xy=True)
    transformer = groupe.transformers[0] if groupe.transformers else None
    avertissements: list[str] = []
    changement_datum = src.datum is not None and dst.datum is not None and src.datum != dst.datum
    if changement_datum and (transformer is None or not groupe.best_available):
        nom_src = src.datum.name if src.datum is not None else "?"
        nom_dst = dst.datum.name if dst.datum is not None else "?"
        grilles = _grilles_manquantes(groupe)
        if exige_grille or transformer is None:
            raise TransformUnavailableError(msg.grille_absente(grilles, nom_src, nom_dst))
        avertissements.append(msg.approximation_acceptee(grilles, nom_src, nom_dst))
    reprojete = gdf.to_crs(dst_epsg)
    description = (
        transformer.description if transformer is not None else f"{src.to_epsg()}->{dst_epsg}"
    )
    return reprojete, description, avertissements


def _resolve_target(
    analysis: AnalysisResult, decision: Decision, profile: RegionProfile
) -> tuple[int | None, str]:
    """(epsg_cible, action) — résout la cible d'exécution depuis la Decision."""
    target = target_family(analysis.famille)
    if decision.choix == "recommendation":
        return analysis.recommandation.cible_epsg, analysis.recommandation.action
    if decision.choix == "zone":
        if decision.zone is None:
            raise ValueError("Decision.choix == 'zone' exige Decision.zone")
        return zone_epsg(fuseau_par_zone(profile, decision.zone), target), "zone"
    if decision.choix == "lambert":
        return lambert_epsg(profile, target), "lambert"
    if decision.choix == "split":
        return None, "split"
    raise ValueError(f"Decision.choix inconnu : {decision.choix!r}")


def _write_layer(
    gdf: gpd.GeoDataFrame,
    out_dir: Path,
    name: str,
    epsg: int,
    zone: int | None,
    out_format: str,
    overwrite: bool,
) -> FichierProduit:
    """Écrit une couche, refuse d'écraser sans overwrite, renvoie le FichierProduit."""
    ext = _FORMATS[out_format][1]
    nom = f"{name}_epsg{epsg}.{ext}" if zone is None else f"{name}_zone{zone}_epsg{epsg}.{ext}"
    chemin = out_dir / nom
    if chemin.exists() and not overwrite:
        raise OutputExistsError(msg.fichier_existant(str(chemin)))
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf.to_file(chemin, driver=_FORMATS[out_format][0])
    return FichierProduit(chemin=str(chemin), epsg=epsg, zone=zone, n_entites=len(gdf))


def _assign_majority(
    layer: gpd.GeoDataFrame, grid: gpd.GeoDataFrame, measure_crs: int
) -> tuple[dict[int, gpd.GeoDataFrame], list[str]]:
    """Affecte chaque entité (intacte) au fuseau de recouvrement dominant.

    L'affectation elle-même vit dans `core.decoupage`, partagée avec `analysis`
    qui l'anticipe pour annoncer le nombre de sorties (DT-25) : les deux doivent
    répondre la même chose, sans quoi l'annonce et la réalité divergent.
    """
    layer = layer.reset_index(drop=True)  # groupement par index positionnel unique (M3)
    data = layer.to_crs(measure_crs)
    cells = grid.to_crs(measure_crs)
    affectations = decoupage.zone_par_entite(data, cells)
    avertissements = [
        msg.hors_profil_affecte(zone) for zone, par_repli in affectations if par_repli
    ]
    zone_par_index = dict(zip(data.index, (zone for zone, _ in affectations), strict=True))
    groups: dict[int, gpd.GeoDataFrame] = {}
    for zone in sorted(set(zone_par_index.values())):
        indices = [i for i, z in zone_par_index.items() if z == zone]
        groups[zone] = layer.loc[indices]
    return groups, avertissements


def _write_journal(
    out_dir: Path,
    name: str,
    analysis: AnalysisResult,
    decision: Decision,
    cible_epsg: int | None,
    pipeline: tuple[str, ...],
    fichiers: tuple[FichierProduit, ...],
    avertissements: list[str],
) -> str:
    """Écrit <name>_journal.json (SPEC §9) et renvoie son chemin."""
    # DT-27 : la note ne dépend PAS de l'origine du choix, mais du fait qu'une
    # cible différente de la recommandation ait été retenue. La garder à
    # `origine == "choice"` excluait le chemin **interactif** — précisément
    # celui où un humain choisit délibérément contre la recommandation, donc
    # celui où la trace importe le plus (observation N5, §6.8 du test manuel).
    # `origine == "auto"` applique la recommandation : la condition ne peut pas
    # s'y déclencher, aucune garde spéciale n'est nécessaire.
    note = None
    if cible_epsg is not None and cible_epsg != analysis.recommandation.cible_epsg:
        note = msg.NOTE_CHOIX_HORS_RECO
    journal = {
        "schema_version": 1,
        "analyse": analysis.to_dict(),
        "decision": {
            "choix": decision.choix,
            "origine": decision.origine,
            "zone": decision.zone,
            "cible_epsg": cible_epsg,
            "note": note,
        },
        "pipeline_proj": list(pipeline),
        "fichiers": [
            {"chemin": f.chemin, "epsg": f.epsg, "zone": f.zone, "n_entites": f.n_entites}
            for f in fichiers
        ],
        "avertissements": avertissements,
        "horodatage": datetime.now(UTC).isoformat(),
        "version_outil": crs_zone_toolkit.__version__,
    }
    chemin = out_dir / f"{name}_journal.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(chemin)


def apply(
    layer: gpd.GeoDataFrame,
    name: str,
    analysis: AnalysisResult,
    decision: Decision,
    *,
    profile: RegionProfile,
    grid: gpd.GeoDataFrame,
    out_dir: Path,
    out_format: str = "gpkg",
    overwrite: bool = False,
) -> ApplyResult:
    """Exécute la Decision : reprojection ou découpage, écrit sorties + journal (SPEC §5/§9)."""
    if out_format not in _FORMATS:  # DT-06 : refus net avant tout travail (API publique)
        raise ValueError(msg.format_sortie_invalide(out_format, list(FORMATS_SORTIE)))
    cible_epsg, action = _resolve_target(analysis, decision, profile)
    avertissements: list[str] = []
    if out_format == "shp":
        avertissements.append(msg.AVERTISSEMENT_SHP)

    # DT-01 : le profil dit quelles familles interdisent une transfo approximative.
    # Les cibles restant dans la famille d'entrée (DATA_REFERENCE §1), seul NAD27
    # déclenche le refus ; ailleurs le repli est accepté et journalisé.
    exige_grille = _exige_transformation_exacte(
        analysis.famille,
        target_family(analysis.famille),
        profile.familles_grille_obligatoire,
    )

    fichiers: list[FichierProduit] = []
    pipelines: list[str] = []

    if action == "split":
        # branche découpage : affectation majoritaire par fuseau (SPEC §5)
        target = target_family(analysis.famille)
        measure_crs = profile.multi_zones["csrs"]
        groups, av_split = _assign_majority(layer, grid, measure_crs)
        avertissements.extend(av_split)
        epsg_par_zone = {
            zone: zone_epsg(fuseau_par_zone(profile, zone), target) for zone in sorted(groups)
        }
        if not overwrite:
            # M1 : pré-vérification atomique — refuse AVANT d'écrire quoi que ce
            # soit si une collision existe sur n'importe quel fichier de zone,
            # pour ne jamais laisser un découpage partiel sur le disque.
            ext = _FORMATS[out_format][1]
            for zone, epsg in epsg_par_zone.items():
                chemin = out_dir / f"{name}_zone{zone}_epsg{epsg}.{ext}"
                if chemin.exists():
                    raise OutputExistsError(msg.fichier_existant(str(chemin)))
        for zone in sorted(groups):
            epsg = epsg_par_zone[zone]
            reprojete, pipeline, av_reproj = _reproject(
                groups[zone], epsg, exige_grille=exige_grille
            )
            pipelines.append(pipeline)
            avertissements.extend(av_reproj)
            fichiers.append(
                _write_layer(reprojete, out_dir, name, epsg, zone, out_format, overwrite)
            )
    elif action == "aucune":
        pass  # 100 % hors profil : aucune sortie de données, journal seul
    else:
        assert cible_epsg is not None
        reprojete, pipeline, av_reproj = _reproject(layer, cible_epsg, exige_grille=exige_grille)
        pipelines.append(pipeline)
        avertissements.extend(av_reproj)
        fichiers.append(
            _write_layer(reprojete, out_dir, name, cible_epsg, None, out_format, overwrite)
        )

    journal = _write_journal(
        out_dir,
        name,
        analysis,
        decision,
        cible_epsg,
        tuple(pipelines),
        tuple(fichiers),
        avertissements,
    )
    return ApplyResult(tuple(fichiers), tuple(pipelines), journal, tuple(avertissements))
