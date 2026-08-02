"""Préparation de la couche : CRS absent, couche vide, make_valid (SPEC §10)."""

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from crs_zone_toolkit.core.analysis import _prepare_layer
from crs_zone_toolkit.core.errors import EmptyLayerError, MissingCrsError


def test_couche_vide_leve() -> None:
    vide = gpd.GeoDataFrame(geometry=[], crs=4326)
    with pytest.raises(EmptyLayerError):
        _prepare_layer(vide, None)


def test_crs_absent_sans_assume_leve() -> None:
    sans_crs = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)])
    with pytest.raises(MissingCrsError):
        _prepare_layer(sans_crs, None)


def test_assume_crs_pose_le_crs_et_avertit() -> None:
    sans_crs = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)])
    gdf, suppose, warnings = _prepare_layer(sans_crs, "EPSG:2949")
    assert suppose is True
    assert gdf.crs.to_epsg() == 2949
    assert any("supposé" in w.lower() for w in warnings)


def test_geometrie_papillon_reparee_avec_avertissement() -> None:
    papillon = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])  # auto-intersection
    gdf = gpd.GeoDataFrame(geometry=[papillon], crs=4326)
    repare, _suppose, warnings = _prepare_layer(gdf, None)
    assert repare.geometry.is_valid.all()
    assert any("make_valid" in w.lower() or "réparé" in w.lower() for w in warnings)
