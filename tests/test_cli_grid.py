"""CLI : commande grid (TP-30, TP-31, TP-32)."""

from pathlib import Path

import geopandas as gpd
from typer.testing import CliRunner

from crs_zone_toolkit.cli import app

runner = CliRunner()
_ATTRS = {"zone", "epsg_csrs", "epsg_nad83", "epsg_nad27", "meridien_central", "lon_min", "lon_max"}


def test_grid_defaut_9_fuseaux_attributs(tmp_path: Path) -> None:  # TP-30
    dst = tmp_path / "g.geojson"
    res = runner.invoke(app, ["grid", "--out", str(dst)])
    assert res.exit_code == 0
    g = gpd.read_file(dst)
    assert len(g) == 9
    assert set(g.columns) >= _ATTRS
    # epsg_nad27 non nul pour fuseaux 2–6 seulement
    par_zone = g.set_index("zone")
    assert par_zone.loc[2, "epsg_nad27"] is not None
    assert g["geometry"].notna().all()


def test_grid_no_clip_contient_le_clip(tmp_path: Path) -> None:  # TP-31
    clip = tmp_path / "clip.geojson"
    noclip = tmp_path / "noclip.geojson"
    runner.invoke(app, ["grid", "--out", str(clip)])
    res = runner.invoke(app, ["grid", "--out", str(noclip), "--no-clip"])
    assert res.exit_code == 0
    gc = gpd.read_file(clip)
    gn = gpd.read_file(noclip)
    # la bande complète (no-clip) doit contenir la version découpée (clip)
    gc_par_zone = gc.set_index("zone").geometry
    gn_par_zone = gn.set_index("zone").geometry
    for zone in gc_par_zone.index:
        # la bande complète (no-clip) doit contenir la version découpée (clip)
        assert gn_par_zone[zone].buffer(1e-9).covers(gc_par_zone[zone])


def test_grid_format_invalide_exit2_propre(tmp_path: Path) -> None:  # revue globale
    dst = tmp_path / "g.geojson"
    res = runner.invoke(app, ["grid", "--out", str(dst), "--format", "shp"])
    assert res.exit_code == 2
    assert res.exception is None or isinstance(res.exception, SystemExit)  # BadParameter propre
    assert not dst.exists()


def test_grid_egale_grille_committee(tmp_path: Path, qc_grid) -> None:  # TP-32
    """La grille regénérée par la CLI égale la grille committée du profil.

    La référence est lue par `load_grid` (fixture `qc_grid`), c'est-à-dire par le
    chemin même dont le moteur se sert — package-relatif, donc valable à
    l'identique au dépôt, dans le sdist déplié et depuis le paquet installé.
    Elle était lue par un chemin relatif au cwd (DT-08) : le seul de la suite, et
    le test tombait dès qu'on lançait pytest d'ailleurs que la racine du dépôt,
    alors que `scripts/`/DT-21 promettent une suite rejouable depuis l'archive.
    """
    dst = tmp_path / "regen.geojson"
    runner.invoke(app, ["grid", "--out", str(dst)])
    regen = gpd.read_file(dst).sort_values("zone").reset_index(drop=True)
    committee = qc_grid.sort_values("zone").reset_index(drop=True)
    assert list(regen["zone"]) == list(committee["zone"])
    assert regen.geometry.geom_equals_exact(committee.geometry, tolerance=1e-6).all()
