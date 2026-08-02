"""CLI : commande apply, modes non interactifs (TP-20, 21, 24, 25, 26)."""

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point
from typer.testing import CliRunner

import crs_zone_toolkit.cli as cli_mod
from crs_zone_toolkit.cli import app

runner = CliRunner()


def _ecrire(gdf, dossier, nom="couche", driver="GPKG", ext="gpkg"):
    chemin = Path(dossier) / f"{nom}.{ext}"
    gdf.to_file(chemin, driver=driver)
    return chemin


def _mono_fuseau7(tmp_path):
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    return _ecrire(gdf, tmp_path, nom="hydro")


def _deux_fuseaux(tmp_path):
    # TP-02 : lignes traversant 75°O + 2 lignes exclusives au fuseau 8 (cf. J3 TP-21)
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    lignes += [
        LineString([(-73.5, 46.0), (-72.5, 46.0)]),
        LineString([(-73.4, 46.3), (-72.6, 46.3)]),
    ]
    gdf = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    return _ecrire(gdf, tmp_path, nom="routes", driver="GeoJSON", ext="geojson")


def test_tp20_auto_reprojection(tmp_path):  # TP-20
    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)])
    assert res.exit_code == 0
    produit = tmp_path / "hydro_epsg2949.gpkg"
    assert produit.exists()
    out = gpd.read_file(produit)
    assert out.crs.to_epsg() == 2949
    assert len(out) == 2
    assert (tmp_path / "hydro_journal.json").exists()


def test_dt20n5_apply_auto_et_choice_invoquent_resume_analyse_abrege(tmp_path, monkeypatch):
    # DT-20 n°5, revue relecteur frais (constat Important 1)
    """Câblage : `apply` invoque `affichage.resume_analyse(..., abrege=True)` exactement une
    fois avant `_resoudre_decision`, aussi bien sous `--auto` que sous `--choice` (SPEC §5.2,
    CLI_UX §5). Espionne l'appel réel (comptage + capture du mot-clé `abrege`) plutôt que la
    sortie terminal : TEST_PLAN §7 réserve les assertions de texte au fichier doré
    `tests/test_affichage_maquette.py`. Signal réel : ce test échoue sur le code d'avant le
    correctif (RED constaté et collé au rapport de tâche), contrairement à l'ancienne version
    de ce test qui ne vérifiait qu'exit 0 + fichiers, indépendants de l'appel.
    """
    appels: list[dict] = []
    original = cli_mod.affichage.resume_analyse

    def _espion(*args, **kwargs):
        appels.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(cli_mod.affichage, "resume_analyse", _espion)

    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)])
    assert res.exit_code == 0
    assert (tmp_path / "hydro_epsg2949.gpkg").exists()
    assert len(appels) == 1
    assert appels[0]["abrege"] is True

    appels.clear()
    src2 = _deux_fuseaux(tmp_path)
    res2 = runner.invoke(app, ["apply", str(src2), "--choice", "split", "--out", str(tmp_path)])
    assert res2.exit_code == 0
    assert len(appels) == 1
    assert appels[0]["abrege"] is True


def test_tp21_choice_split_deux_fichiers(tmp_path):  # TP-21
    src = _deux_fuseaux(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--choice", "split", "--out", str(tmp_path)])
    assert res.exit_code == 0
    # Aucun --format : défaut GeoPackage (SPEC §5) — cf. test_apply.py TP-21 (noyau).
    produits = sorted(tmp_path.glob("routes_zone*_epsg*.gpkg"))
    total = sum(len(gpd.read_file(p)) for p in produits)
    assert len(produits) == 2
    assert total == 5  # somme = entités d'origine, aucune coupée/dupliquée


def test_tp24_refus_ecraser_puis_overwrite(tmp_path):  # TP-24
    src = _mono_fuseau7(tmp_path)
    assert runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)]).exit_code == 0
    r2 = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)])
    assert r2.exit_code == 2  # OutputExistsError
    r3 = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path), "--overwrite"])
    assert r3.exit_code == 0


def test_tp25_non_interactif_nu_exit_2(tmp_path):  # TP-25
    src = _deux_fuseaux(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)])
    assert res.exit_code == 2  # NonInteractiveError (pas de TTY, ni --auto ni --choice)


def test_tp26_choice_zone_note_contre_reco(tmp_path):  # TP-26
    src = _deux_fuseaux(tmp_path)
    res = runner.invoke(
        app, ["apply", str(src), "--choice", "zone", "--zone", "9", "--out", str(tmp_path)]
    )
    assert res.exit_code == 0
    journal = json.loads((tmp_path / "routes_journal.json").read_text(encoding="utf-8"))
    assert journal["decision"]["choix"] == "zone"
    from crs_zone_toolkit.core import messages

    assert journal["decision"]["note"] == messages.NOTE_CHOIX_HORS_RECO


def _sortie_propre(res) -> bool:
    """Vrai si la sortie est un SystemExit contrôlé (jamais une exception brute, SPEC §10)."""
    return res.exception is None or isinstance(res.exception, SystemExit)


def test_choice_bogus_exit2_propre(tmp_path):  # revue Task 7, issue 1
    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--choice", "bogus", "--out", str(tmp_path)])
    assert res.exit_code == 2
    assert _sortie_propre(res)  # BadParameter : sortie propre, aucune trace brute


def test_choice_zone_sans_fuseau_traverse_exit2_propre(  # revue Task 7, issue 2
    tmp_path, hors_profil_total_points
):
    src = _ecrire(hors_profil_total_points, tmp_path, nom="hors_profil")
    res = runner.invoke(app, ["apply", str(src), "--choice", "zone", "--out", str(tmp_path)])
    assert res.exit_code == 2
    assert _sortie_propre(res)  # aucune ValueError brute (SPEC §10)


def test_choice_zone_fuseau_absent_du_profil_exit2_propre(tmp_path):  # revue Task 7, issue 2/3
    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(
        app, ["apply", str(src), "--choice", "zone", "--zone", "99", "--out", str(tmp_path)]
    )
    assert res.exit_code == 2
    assert _sortie_propre(res)


def test_interactif_defaut_applique_reco(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_mod, "_est_interactif", lambda: True)
    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)], input="1\n")
    assert res.exit_code == 0
    # reco pour _mono_fuseau7 = MTM 7 (EPSG:2949) : reprojection sans frontière de
    # datum, donc sans grille PROJ (le Lambert 6622 exigerait ca_nrc_NA83SCRS.tif, cf. limite J6).
    produit = tmp_path / "hydro_epsg2949.gpkg"
    assert produit.exists()
    produits = list(tmp_path.glob("hydro_epsg*.gpkg"))
    assert len(produits) == 1


def test_interactif_annulation_zero_exit_0_sans_ecrit(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_mod, "_est_interactif", lambda: True)
    src = _deux_fuseaux(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)], input="0\n")
    assert res.exit_code == 0
    assert not list(tmp_path.glob("routes_epsg*.gpkg"))
    assert not (tmp_path / "routes_journal.json").exists()


def test_interactif_entree_vide_defaut_reco(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_mod, "_est_interactif", lambda: True)
    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)], input="\n")
    assert res.exit_code == 0
    # même raison que test_interactif_defaut_applique_reco ci-dessus : cible MTM, pas Lambert.
    produit = tmp_path / "hydro_epsg2949.gpkg"
    assert produit.exists()
    assert len(list(tmp_path.glob("hydro_epsg*.gpkg"))) == 1


def test_format_invalide_exit2_propre(tmp_path):  # revue globale
    src = _mono_fuseau7(tmp_path)
    res = runner.invoke(
        app, ["apply", str(src), "--auto", "--format", "kml", "--out", str(tmp_path)]
    )
    assert res.exit_code == 2
    assert _sortie_propre(res)  # BadParameter : sortie propre, aucune KeyError brute
    assert not list(tmp_path.glob("hydro_epsg*"))
    assert not (tmp_path / "hydro_journal.json").exists()


def test_interactif_choix_2_sous_invite_fuseau(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_mod, "_est_interactif", lambda: True)
    src = _deux_fuseaux(tmp_path)
    # [2] fuseau unique, puis sous-invite → fuseau 9
    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)], input="2\n9\n")
    assert res.exit_code == 0
    import json

    journal = json.loads((tmp_path / "routes_journal.json").read_text(encoding="utf-8"))
    assert journal["decision"]["choix"] == "zone"
    assert journal["decision"]["zone"] == 9
