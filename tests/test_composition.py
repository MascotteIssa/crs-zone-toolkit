"""Helpers de composition partagés (_charger_et_analyser, _prepare_source_layer)."""

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

import crs_zone_toolkit
from crs_zone_toolkit.core.errors import LayerReadError, MissingCrsError


def _shp_sans_prj(tmp_path: Path) -> Path:
    gdf = gpd.GeoDataFrame(geometry=[Point(297000, 5029000)], crs="EPSG:2950")
    src = tmp_path / "sans_prj.shp"
    gdf.to_file(src, driver="ESRI Shapefile")
    src.with_suffix(".prj").unlink()  # source sans CRS déclaré
    return src


def test_charger_et_analyser_couche_prete_et_resultat(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = tmp_path / "couche.geojson"
    gdf.to_file(src, driver="GeoJSON")
    layer, result, profile, grid = crs_zone_toolkit._charger_et_analyser(src)
    assert layer.crs is not None
    assert result.recommandation.cible_epsg == 2949  # fuseau 7
    assert profile.id == "qc"
    assert len(grid) == 9


def test_charger_et_analyser_assume_crs_conserve_avertissement(tmp_path: Path) -> None:
    """Le warning « CRS supposé » doit survivre (analyse AVANT assignation)."""
    src = _shp_sans_prj(tmp_path)
    layer, result, _, _ = crs_zone_toolkit._charger_et_analyser(src, assume_crs="EPSG:2950")
    assert layer.crs is not None and layer.crs.to_epsg() == 2950
    assert crs_zone_toolkit.core.messages.CRS_SUPPOSE in result.avertissements


def test_charger_et_analyser_sans_crs_leve(tmp_path: Path) -> None:
    src = _shp_sans_prj(tmp_path)
    with pytest.raises(MissingCrsError):
        crs_zone_toolkit._charger_et_analyser(src)


def test_charger_et_analyser_chemin_inexistant_message_introuvable(tmp_path: Path) -> None:
    """DT-11 : chemin inexistant → message distinct « vérifiez le chemin »."""
    with pytest.raises(LayerReadError, match="[Vv]érifiez le chemin"):
        crs_zone_toolkit._charger_et_analyser(tmp_path / "absent.gpkg")


def test_charger_et_analyser_format_non_geospatial_message_formats(tmp_path: Path) -> None:
    """DT-11 : fichier existant mais illisible comme couche → message nommant les formats."""
    chemin = tmp_path / "faux.gpkg"
    chemin.write_text("ceci n'est pas un geopackage")
    with pytest.raises(LayerReadError, match="[Ff]ormats pris en charge"):
        crs_zone_toolkit._charger_et_analyser(chemin)


def test_apply_public_journal_note_crs_suppose(tmp_path: Path) -> None:
    """Régression : apply() doit désormais tracer « CRS supposé » (SPEC §4.2.2)."""
    src = _shp_sans_prj(tmp_path)
    from crs_zone_toolkit.core.results import Decision

    res = crs_zone_toolkit.apply(
        src, Decision("recommendation", "auto"), assume_crs="EPSG:2950", out_dir=tmp_path
    )
    journal = json.loads(Path(res.journal).read_text(encoding="utf-8"))
    assert crs_zone_toolkit.core.messages.CRS_SUPPOSE in journal["analyse"]["avertissements"]
