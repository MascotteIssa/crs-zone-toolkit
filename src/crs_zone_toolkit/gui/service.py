"""Façade pure entre l'interface de bureau et l'API publique du paquet.

N'appelle jamais crs_zone_toolkit.core.* directement — seulement
crs_zone_toolkit.analyze/apply/report/generate_grid, comme cli.py. Sans
aucune dépendance à pywebview : testable sans ouvrir de fenêtre.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import crs_zone_toolkit
from crs_zone_toolkit.core.results import Decision

if TYPE_CHECKING:
    from crs_zone_toolkit.core.results import AnalysisResult, ApplyResult

_CHOIX_VALIDES = ("recommendation", "lambert", "split")


def run_analyze(
    source: Path, *, region: str = "qc", assume_crs: str | None = None
) -> AnalysisResult:
    return crs_zone_toolkit.analyze(source, region=region, assume_crs=assume_crs)


def run_report(
    source: Path, *, region: str = "qc", out_dir: Path | None = None, assume_crs: str | None = None
) -> Path:
    return crs_zone_toolkit.report(source, region=region, out_dir=out_dir, assume_crs=assume_crs)


def decision_from_choice(choice: str) -> Decision:
    if choice not in _CHOIX_VALIDES:
        raise ValueError(
            f"Choix de décision non reconnu : {choice!r}. Attendu : {', '.join(_CHOIX_VALIDES)}."
        )
    return Decision(choice, "choice")


def run_apply(
    source: Path,
    decision: Decision,
    *,
    region: str = "qc",
    out_dir: Path | None = None,
    out_format: str = "gpkg",
    overwrite: bool = False,
) -> ApplyResult:
    return crs_zone_toolkit.apply(
        source,
        decision,
        region=region,
        out_dir=out_dir,
        out_format=out_format,
        overwrite=overwrite,
    )


def run_generate_grid(
    *, region: str = "qc", out: Path, out_format: str = "geojson", clip: bool = True
) -> tuple[Path, int, tuple[str, ...]]:
    return crs_zone_toolkit.generate_grid(region=region, out=out, out_format=out_format, clip=clip)
