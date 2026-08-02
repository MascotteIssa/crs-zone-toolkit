"""Reprojection + capture du pipeline PROJ (DATA_REFERENCE §6.1).

`_reproject` arbitre aussi le repli « ballpark » (DT-01) : il refuse quand la
famille est déclarée à risque par le profil (`exige_grille=True`), sinon il
accepte en avertissant. Ces tests restent insensibles aux grilles PROJ
installées : le fuseau MTM 7 (2949) n'exige aucune transformation de datum
depuis WGS84, et le cas « refus » est piloté par le drapeau, pas par la machine.
"""

import geopandas as gpd
import pytest
from shapely.geometry import Point

from crs_zone_toolkit.core.apply import _reproject
from crs_zone_toolkit.core.errors import TransformUnavailableError


def test_reproject_change_le_crs_et_capture_le_pipeline() -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    out, pipeline, avertissements = _reproject(gdf, 2949, exige_grille=False)  # WGS84 -> MTM 7
    assert out.crs.to_epsg() == 2949
    assert isinstance(pipeline, str) and pipeline.strip()
    # coordonnées projetées (mètres) : loin de l'origine géographique
    assert abs(out.geometry.iloc[0].x) > 1000
    # aucune transformation de datum en jeu ici : rien à signaler
    assert avertissements == []


def test_reproject_refuse_le_ballpark_quand_la_famille_l_exige() -> None:
    """DT-01 : `exige_grille` est le seul arbitre du refus (familles déclarées au profil)."""
    # NAD27 géographique -> MTM 7 CSRS : vrai changement de datum (dizaines de
    # mètres), et la grille NTv2 n'est pas distribuée avec pyproj.
    nad27 = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4267)
    with pytest.raises(TransformUnavailableError):
        _reproject(nad27, 2949, exige_grille=True)
