"""CLI : squelette, options globales, codes de sortie, commande analyze."""

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point
from typer.testing import CliRunner

from crs_zone_toolkit.cli import app

runner = CliRunner()


def _ecrire(gdf, dossier, nom="couche", driver="GPKG", ext="gpkg"):
    chemin = Path(dossier) / f"{nom}.{ext}"
    gdf.to_file(chemin, driver=driver)
    return chemin


def test_version() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "crszone" in res.stdout


def test_aide_liste_les_commandes() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    for cmd in ("analyze", "apply", "grid"):
        assert cmd in res.stdout


def test_region_inconnue_exit_1(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = _ecrire(gdf, tmp_path)
    res = runner.invoke(app, ["--region", "zz", "analyze", str(src)])
    assert res.exit_code == 1  # UnknownRegionError → code 1


def test_fichier_introuvable_exit_1(tmp_path: Path) -> None:
    res = runner.invoke(app, ["analyze", str(tmp_path / "absent.gpkg")])
    assert res.exit_code == 1  # LayerReadError → code 1


def test_analyze_ecrit_rapport_exit_0(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = _ecrire(gdf, tmp_path, nom="hydro")
    res = runner.invoke(app, ["analyze", str(src)])
    assert res.exit_code == 0
    assert list(tmp_path.glob("hydro_analyse_crs_*.html"))  # nom horodaté


def test_analyze_report_dossier(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = _ecrire(gdf, tmp_path, nom="hydro")
    dossier = tmp_path / "rapports"
    dossier.mkdir()
    res = runner.invoke(app, ["analyze", str(src), "--report", str(dossier)])
    assert res.exit_code == 0
    assert list(dossier.glob("hydro_analyse_crs_*.html"))  # nom horodaté


def test_analyze_deux_fois_regenere_sans_erreur(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = _ecrire(gdf, tmp_path, nom="hydro")
    assert runner.invoke(app, ["analyze", str(src)]).exit_code == 0
    assert runner.invoke(app, ["analyze", str(src)]).exit_code == 0  # overwrite=True


def test_tp33_json_seul_sur_stdout(tmp_path: Path) -> None:  # TP-33
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = _ecrire(gdf, tmp_path)
    res = runner.invoke(app, ["analyze", str(src), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)  # stdout = JSON pur, parsable
    assert data["schema_version"] == 1
    assert "recommandation" in data


def test_json_out_ecrit_fichier(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = _ecrire(gdf, tmp_path)
    dst = tmp_path / "analyse.json"
    res = runner.invoke(app, ["analyze", str(src), "--json-out", str(dst)])
    assert res.exit_code == 0
    assert json.loads(dst.read_text(encoding="utf-8"))["schema_version"] == 1


def test_tp06_sans_crs_exit_2(tmp_path: Path) -> None:  # TP-06
    gdf = gpd.GeoDataFrame(geometry=[Point(-73.5, 46.0)], crs=4326)
    base = tmp_path / "sans_prj.shp"
    gdf.to_file(base, driver="ESRI Shapefile")
    base.with_suffix(".prj").unlink()
    res = runner.invoke(app, ["analyze", str(base)])
    assert res.exit_code == 2  # MissingCrsError → code 2
    assert not (tmp_path / "sans_prj_analyse_crs.html").exists()  # aucun rapport


def test_tp06_avec_assume_crs_warning_dans_json(tmp_path: Path) -> None:  # TP-06
    gdf = gpd.GeoDataFrame(geometry=[Point(-73.5, 46.0), Point(-73.4, 46.1)], crs=4326)
    base = tmp_path / "sans_prj.shp"
    gdf.to_file(base, driver="ESRI Shapefile")
    base.with_suffix(".prj").unlink()
    res = runner.invoke(app, ["analyze", str(base), "--assume-crs", "EPSG:2950", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["crs_entree"]["suppose"] is True
    from crs_zone_toolkit.core import messages

    assert messages.CRS_SUPPOSE in data["avertissements"]
