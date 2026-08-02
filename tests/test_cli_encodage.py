"""DT-15 : la CLI force l'UTF-8 sur ses flux pour survivre à une console
non-UTF-8 (Windows cp1252 en redirection) — le « → » de la recommandation
plantait (UnicodeEncodeError) et --json ressortait en mojibake."""

import io
import os
import subprocess
import sys

import geopandas as gpd
from shapely.geometry import Point
from typer.testing import CliRunner

from crs_zone_toolkit import cli


def _run_cli_cp1252(args: list[str], cwd=None) -> subprocess.CompletedProcess[bytes]:
    """Lance la CLI dans un sous-processus dont la console est cp1252 et la sortie
    redirigée (pas un tty) — reproduit la console Windows du test manuel J6.
    Invoque `cli:app` exactement comme le point d'entrée console."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    argv = ["crszone", *args]
    code = f"import sys; sys.argv={argv!r}; from crs_zone_toolkit.cli import app; app()"
    return subprocess.run([sys.executable, "-c", code], capture_output=True, cwd=cwd, env=env)


def test_dt15_flux_cp1252_reconfigure_en_utf8(monkeypatch) -> None:
    brut_out, brut_err = io.BytesIO(), io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(brut_out, encoding="cp1252"))
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(brut_err, encoding="cp1252"))

    cli._forcer_utf8()

    assert sys.stdout.encoding.lower() == "utf-8"
    assert sys.stderr.encoding.lower() == "utf-8"
    # « → » (U+2192) est hors cp1252 : sans reconfiguration, ce write planterait.
    sys.stdout.write("→ Recommandation")
    sys.stdout.flush()
    assert brut_out.getvalue().decode("utf-8") == "→ Recommandation"


def test_dt15_callback_force_utf8(monkeypatch, tmp_path) -> None:
    appele = {"v": False}
    monkeypatch.setattr(cli, "_forcer_utf8", lambda: appele.__setitem__("v", True))
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = tmp_path / "couche.gpkg"
    gdf.to_file(src, driver="GPKG")

    res = CliRunner().invoke(cli.app, ["analyze", str(src)])

    assert res.exit_code == 0
    assert appele["v"] is True


def test_dt15_help_sous_cp1252_ne_plante_pas() -> None:
    # `--help` (option eager) sort AVANT le callback : l'aide de `apply` contient
    # un « → » (analyser → décider → agir). Le forçage UTF-8 doit agir plus tôt.
    res = _run_cli_cp1252(["--help"])

    assert res.returncode == 0
    sortie = res.stdout.decode("utf-8")  # UTF-8 valide, ne doit pas lever
    assert "→" in sortie


def test_dt15_analyze_sous_cp1252_sort_en_utf8(tmp_path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = tmp_path / "couche.gpkg"
    gdf.to_file(src, driver="GPKG")

    res = _run_cli_cp1252(["analyze", str(src)], cwd=tmp_path)

    assert res.returncode == 0
    sortie = res.stdout.decode("utf-8")  # « → Recommandation » sans mojibake ni crash
    assert "→" in sortie
