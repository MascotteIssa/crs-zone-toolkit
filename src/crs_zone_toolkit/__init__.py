"""crs-zone-toolkit — analyse, recommandation et reprojection CRS (profils régionaux, V1 : Québec).

API publique (contrat : docs/ARCHITECTURE.md §4) :
    from crs_zone_toolkit import analyze, apply, report
`analyze` (recommandation CRS), `apply` (exécution d'une décision) et
`report` (rapport HTML d'analyse) sont implémentées et exportées.
`generate_grid` (génération de grille MTM) reste un outil de développement
interne (docs/gridgen), pas encore exposé ici.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from crs_zone_toolkit.core.results import AnalysisResult, ApplyResult, Decision

if TYPE_CHECKING:
    import geopandas as gpd

    from crs_zone_toolkit.core.profile import RegionProfile

__version__ = "0.1.0"

_FORMATS_GRILLE: dict[str, str] = {"geojson": "GeoJSON", "gpkg": "GPKG"}
FORMATS_GRILLE: tuple[str, ...] = tuple(sorted(_FORMATS_GRILLE))
"""Formats d'écriture de la grille (SPEC §6 : geojson | gpkg — pas de shapefile)."""


def _prepare_source_layer(
    layer: gpd.GeoDataFrame, assume_crs: str | int | None
) -> gpd.GeoDataFrame:
    """Assigne le CRS supposé à la couche si elle n'en déclare pas (dette J4 #1).

    N'ASSIGNE pas de reprojection : pose seulement l'étiquette CRS quand la source
    est muette et qu'un --assume-crs est fourni. Partagé par apply/report/CLI.
    """
    if layer.crs is None and assume_crs is not None:
        from pyproj import CRS

        return layer.set_crs(CRS.from_user_input(assume_crs))
    return layer


def _charger_et_analyser(
    source: Path | str,
    *,
    region: str = "qc",
    assume_crs: str | int | None = None,
    n_samples: int | None = None,
) -> tuple[gpd.GeoDataFrame, AnalysisResult, RegionProfile, gpd.GeoDataFrame]:
    """Composition partagée : lit et analyse la couche UNE fois (SPEC §6).

    Ordre voulu : analyse AVANT assignation du CRS supposé, pour que
    l'avertissement « CRS supposé » soit capté par le moteur (SPEC §4.2.2).
    Renvoie la couche prête pour l'écriture (CRS assigné) + le résultat + le
    profil + la grille, réutilisables par apply/report/CLI sans re-lecture.
    """
    import geopandas as gpd

    from crs_zone_toolkit.core import analysis as _analysis
    from crs_zone_toolkit.core import messages as _msg
    from crs_zone_toolkit.core.errors import LayerReadError
    from crs_zone_toolkit.regions.loader import load_grid, load_profile

    source = Path(source)
    profile = load_profile(region)
    grid = load_grid(profile)
    if not source.is_file():
        raise LayerReadError(_msg.fichier_introuvable(str(source)))
    try:
        layer = gpd.read_file(source)
    except Exception as exc:  # lecture géospatiale en échec (SPEC §10, code 1)
        raise LayerReadError(_msg.format_non_supporte(str(source))) from exc
    result = _analysis.analyze(
        layer, source.stem, profile=profile, grid=grid, assume_crs=assume_crs, n_samples=n_samples
    )
    layer = _prepare_source_layer(layer, assume_crs)
    return layer, result, profile, grid


def analyze(
    source: Path | str,
    *,
    region: str = "qc",
    assume_crs: str | int | None = None,
    n_samples: int | None = None,
) -> AnalysisResult:
    """Analyse une couche (contrat ARCHITECTURE §4)."""
    _, result, _, _ = _charger_et_analyser(
        source, region=region, assume_crs=assume_crs, n_samples=n_samples
    )
    return result


def apply(
    source: Path | str,
    decision: Decision,
    *,
    region: str = "qc",
    out_dir: Path | str | None = None,
    out_format: str = "gpkg",
    overwrite: bool = False,
    assume_crs: str | int | None = None,
) -> ApplyResult:
    """Exécute une décision sur une couche (contrat ARCHITECTURE §4)."""
    from crs_zone_toolkit.core import apply as _apply

    source = Path(source)
    layer, result, profile, grid = _charger_et_analyser(
        source, region=region, assume_crs=assume_crs
    )
    cible = Path(out_dir) if out_dir is not None else source.parent
    return _apply.apply(
        layer,
        source.stem,
        result,
        decision,
        profile=profile,
        grid=grid,
        out_dir=cible,
        out_format=out_format,
        overwrite=overwrite,
    )


def _generer_grille(
    *,
    region: str = "qc",
    out: Path | str,
    out_format: str = "geojson",
    clip: bool = True,
) -> tuple[Path, int, tuple[str, ...]]:
    """Compose loader + gridgen + écriture ; renvoie (chemin, n_entités, attributs)."""
    if out_format not in _FORMATS_GRILLE:  # DT-19 : même garde que apply (DT-06)
        from crs_zone_toolkit.core import messages as _m

        raise ValueError(_m.format_sortie_invalide(out_format, list(FORMATS_GRILLE)))

    from crs_zone_toolkit.core.gridgen import _ATTRIBUTS, build_grid
    from crs_zone_toolkit.regions.loader import load_boundary, load_profile

    profile = load_profile(region)
    boundary = load_boundary(profile)
    grille = build_grid(profile, boundary, clip=clip)
    out = Path(out)
    if out.parent != Path():
        out.parent.mkdir(parents=True, exist_ok=True)
    grille.to_file(out, driver=_FORMATS_GRILLE[out_format])
    return out, len(grille), _ATTRIBUTS


def report(
    source: Path | str,
    *,
    region: str = "qc",
    out_dir: Path | str | None = None,
    assume_crs: str | int | None = None,
    overwrite: bool = False,
) -> Path:
    """Génère le rapport HTML d'analyse d'une couche (contrat SPEC §7)."""
    from datetime import UTC, datetime

    from crs_zone_toolkit.core import report as _report

    source = Path(source)
    layer, result, profile, grid = _charger_et_analyser(
        source, region=region, assume_crs=assume_crs
    )
    quand = datetime.now(UTC)
    html = _report.render_html(
        result, layer, profile=profile, grid=grid, generated_at=quand, fichier=source.name
    )
    cible = Path(out_dir) if out_dir is not None else source.parent
    return _report._ecrire(html, source, out_dir=cible, overwrite=overwrite, generated_at=quand)


__all__ = ["analyze", "apply", "report", "AnalysisResult", "ApplyResult", "Decision"]
