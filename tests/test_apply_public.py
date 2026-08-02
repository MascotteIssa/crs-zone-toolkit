"""Wrapper public apply(source, decision) — lit un fichier, câble analyze + core.apply."""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

import crs_zone_toolkit
from crs_zone_toolkit.core.results import Decision


def test_apply_public_reprojection(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = tmp_path / "couche.geojson"
    gdf.to_file(src, driver="GeoJSON")
    res = crs_zone_toolkit.apply(src, Decision("recommendation", "auto"), out_dir=tmp_path)
    assert res.fichiers[0].epsg == 2949
    assert Path(res.journal).exists()


def test_apply_public_assume_crs_sur_shapefile_sans_prj(tmp_path: Path) -> None:
    """I1 : --assume-crs doit s'appliquer à la couche réellement reprojetée.

    Un shapefile sans .prj (crs=None au chargement) doit se voir assigner le
    CRS supposé AVANT l'apply, pas seulement dans une copie interne jetée par
    analyze — sinon core.apply reçoit crs=None et pyproj lève une CRSError brute.
    """
    gdf = gpd.GeoDataFrame(
        geometry=[Point(297000, 5029000), Point(297500, 5029500)], crs="EPSG:2950"
    )
    src = tmp_path / "couche.shp"
    gdf.to_file(src, driver="ESRI Shapefile")
    (tmp_path / "couche.prj").unlink()  # simule une source sans CRS déclaré

    res = crs_zone_toolkit.apply(
        src, Decision("recommendation", "auto"), assume_crs="EPSG:2950", out_dir=tmp_path
    )
    assert res.fichiers[0].epsg is not None
    out = gpd.read_file(res.fichiers[0].chemin)
    assert out.crs is not None
    assert out.crs.to_epsg() is not None
