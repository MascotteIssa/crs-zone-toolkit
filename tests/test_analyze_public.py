"""Wrapper public analyze(source, region) — lit un fichier, câble loader + noyau."""

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

import crs_zone_toolkit
from crs_zone_toolkit.core.errors import MissingCrsError


def test_analyze_public_depuis_geojson(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    chemin = tmp_path / "couche.geojson"
    gdf.to_file(chemin, driver="GeoJSON")
    result = crs_zone_toolkit.analyze(chemin)
    data = json.loads(result.to_json())
    assert data["recommandation"]["cible_epsg"] == 2949  # fuseau 7
    assert data["couche"]  # nom de couche renseigné


def test_tp06_shapefile_sans_prj(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-73.5, 46.0)], crs=4326)
    base = tmp_path / "sans_prj.shp"
    gdf.to_file(base)
    base.with_suffix(".prj").unlink()  # supprime la déclaration de CRS
    with pytest.raises(MissingCrsError):
        crs_zone_toolkit.analyze(base)
    ok = crs_zone_toolkit.analyze(base, assume_crs="EPSG:2950")
    assert json.loads(ok.to_json())["crs_entree"]["suppose"] is True
