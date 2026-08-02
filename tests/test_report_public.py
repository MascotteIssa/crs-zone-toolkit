"""Wrapper public report(source) — charge, analyse, rend et écrit le rapport HTML."""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point

import crs_zone_toolkit


def test_report_public_bout_en_bout(tmp_path: Path) -> None:
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    src = tmp_path / "routes.geojson"
    gpd.GeoDataFrame(geometry=lignes, crs=4326).to_file(src, driver="GeoJSON")

    chemin = crs_zone_toolkit.report(src, out_dir=tmp_path)

    assert chemin.parent == tmp_path
    assert chemin.name.startswith("routes_analyse_crs_") and chemin.name.endswith(".html")
    html = chemin.read_text(encoding="utf-8")
    assert "Analyse CRS" in html
    assert "data:image/png;base64," in html


def test_report_public_assume_crs_shapefile_sans_prj(tmp_path: Path) -> None:
    """--assume-crs doit s'appliquer à une source sans .prj (pas de CRSError brute)."""
    gdf = gpd.GeoDataFrame(
        geometry=[Point(297000, 5029000), Point(297500, 5029500)], crs="EPSG:2950"
    )
    src = tmp_path / "c.shp"
    gdf.to_file(src, driver="ESRI Shapefile")
    (tmp_path / "c.prj").unlink()

    chemin = crs_zone_toolkit.report(src, assume_crs="EPSG:2950", out_dir=tmp_path)
    assert chemin.exists()


def test_report_dans_all() -> None:
    assert "report" in crs_zone_toolkit.__all__
