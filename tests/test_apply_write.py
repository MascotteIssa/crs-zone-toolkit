"""Écriture des sorties : nommage, driver, refus d'écraser (SPEC §5.3)."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from crs_zone_toolkit.core.apply import _write_layer
from crs_zone_toolkit.core.errors import OutputExistsError


def _gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=2949)


def test_nommage_reprojection(tmp_path: Path) -> None:
    f = _write_layer(_gdf(), tmp_path, "couche", 2949, None, "gpkg", False)
    assert Path(f.chemin).name == "couche_epsg2949.gpkg"
    assert f.epsg == 2949 and f.zone is None and f.n_entites == 1
    assert Path(f.chemin).exists()


def test_nommage_decoupage(tmp_path: Path) -> None:
    f = _write_layer(_gdf(), tmp_path, "couche", 2950, 8, "gpkg", False)
    assert Path(f.chemin).name == "couche_zone8_epsg2950.gpkg"


def test_refus_ecraser(tmp_path: Path) -> None:
    _write_layer(_gdf(), tmp_path, "couche", 2949, None, "gpkg", False)
    with pytest.raises(OutputExistsError):
        _write_layer(_gdf(), tmp_path, "couche", 2949, None, "gpkg", False)
    # avec overwrite : succès
    _write_layer(_gdf(), tmp_path, "couche", 2949, None, "gpkg", True)
