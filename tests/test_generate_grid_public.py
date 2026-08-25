"""Wrapper public generate_grid(region, out) — expose la génération de grille MTM."""

from pathlib import Path

import crs_zone_toolkit


def test_generate_grid_public_geojson(tmp_path: Path) -> None:
    out = tmp_path / "grille.geojson"
    chemin, n, attributs = crs_zone_toolkit.generate_grid(
        region="qc", out=out, out_format="geojson"
    )
    assert chemin.exists()
    assert n > 0
    assert attributs == (
        "zone",
        "epsg_csrs",
        "epsg_nad83",
        "epsg_nad27",
        "meridien_central",
        "lon_min",
        "lon_max",
    )
