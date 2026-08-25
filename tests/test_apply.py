"""Cas TP-20 à TP-27 : exécution (assertions sur fichiers produits + journal JSON)."""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from crs_zone_toolkit.core.analysis import analyze
from crs_zone_toolkit.core.apply import apply
from crs_zone_toolkit.core.errors import OutputExistsError
from crs_zone_toolkit.core.results import Decision


def _run(layer, decision, qc_profile, qc_grid, out_dir, **kw):
    analysis = analyze(layer, "couche", profile=qc_profile, grid=qc_grid)
    return apply(
        layer,
        "couche",
        analysis,
        decision,
        profile=qc_profile,
        grid=qc_grid,
        out_dir=out_dir,
        **kw,
    )


def test_tp20_reprojection_simple(tp01_points_fuseau7, qc_profile, qc_grid, tmp_path) -> None:
    res = _run(
        tp01_points_fuseau7,
        Decision("recommendation", "auto"),
        qc_profile,
        qc_grid,
        tmp_path,
    )
    assert len(res.fichiers) == 1
    f = res.fichiers[0]
    assert Path(f.chemin).name == "couche_epsg2949.gpkg"
    assert f.epsg == 2949 and f.n_entites == 50  # effectif conservé
    out = gpd.read_file(f.chemin)
    assert out.crs.to_epsg() == 2949
    assert Path(res.journal).exists()
    data = json.loads(Path(res.journal).read_text(encoding="utf-8"))
    assert data["fichiers"][0]["epsg"] == 2949


def test_tp21_decoupage_deux_fuseaux(
    tp02_lignes_deux_fuseaux, qc_profile, qc_grid, tmp_path
) -> None:
    """TP-21 : découpage par majorité, conservation des entités (2 fuseaux).

    Les 3 lignes de tp02_lignes_deux_fuseaux ont toutes le même ratio (58 % zone 9
    / 42 % zone 8 — vérifié : 1,16° en zone 9 contre 0,84° en zone 8, quel que soit
    leur latitude) : l'affectation par majorité (entité entière, jamais découpée)
    les envoie donc TOUTES en zone 9. Pour exercer un vrai découpage à deux
    fuseaux, on ajoute 2 lignes entièrement en zone 8 (lon -74,5 à -73,5).
    """
    extra_zone8 = gpd.GeoDataFrame(
        geometry=[
            LineString([(-74.5, 46.6), (-73.5, 46.6)]),
            LineString([(-74.5, 46.8), (-73.5, 46.8)]),
        ],
        crs=4326,
    )
    couche = gpd.GeoDataFrame(
        pd.concat([tp02_lignes_deux_fuseaux, extra_zone8], ignore_index=True), crs=4326
    )
    res = _run(couche, Decision("split", "choice"), qc_profile, qc_grid, tmp_path)
    zones = {f.zone for f in res.fichiers}
    assert zones == {8, 9}
    noms = sorted(Path(f.chemin).name for f in res.fichiers)
    assert noms == ["couche_zone8_epsg2950.gpkg", "couche_zone9_epsg2951.gpkg"]
    total = sum(f.n_entites for f in res.fichiers)
    assert total == len(couche)  # aucune entité perdue ni dupliquée


def test_tp22_majorite_surface_pas_centroide(
    tp22_croissant_a_cheval, qc_profile, qc_grid, tmp_path
) -> None:
    """TP-22 : le croissant a plus de surface en fuseau 8 mais un centroïde en
    fuseau 9 (vérifié dans la fixture) — l'affectation doit suivre la surface."""
    res = _run(tp22_croissant_a_cheval, Decision("split", "choice"), qc_profile, qc_grid, tmp_path)
    zones = {f.zone for f in res.fichiers}
    assert zones == {8}  # majorité surfacique fuseau 8, malgré le centroïde côté 9


def test_tp23_ligne_majorite_longueur(
    tp23_ligne_majorite_fuseau9, qc_profile, qc_grid, tmp_path
) -> None:
    """TP-23 : ligne à 70 % de sa longueur en fuseau 9 → affectée entièrement à 9."""
    res = _run(
        tp23_ligne_majorite_fuseau9, Decision("split", "choice"), qc_profile, qc_grid, tmp_path
    )
    assert {f.zone for f in res.fichiers} == {9}


def test_tp24_refus_ecraser(tp01_points_fuseau7, qc_profile, qc_grid, tmp_path) -> None:
    """TP-24: Refus d'écraser un fichier existant, puis succès avec overwrite=True."""
    d = Decision("recommendation", "auto")
    # Première exécution : succès
    _run(tp01_points_fuseau7, d, qc_profile, qc_grid, tmp_path)
    # Deuxième exécution sans overwrite : levée d'OutputExistsError
    with pytest.raises(OutputExistsError):
        _run(tp01_points_fuseau7, d, qc_profile, qc_grid, tmp_path)
    # Troisième exécution avec overwrite=True : succès
    res = _run(tp01_points_fuseau7, d, qc_profile, qc_grid, tmp_path, overwrite=True)
    assert res.fichiers[0].epsg == 2949


def test_tp26_note_choix_hors_reco(tp02_lignes_deux_fuseaux, qc_profile, qc_grid, tmp_path) -> None:
    """TP-26 : note journal « choix utilisateur ≠ recommandation ».

    TP-02 → recommandation = fuseau MTM 9 (CSRS 2951, règle B2) ; l'utilisateur
    impose le Québec Lambert (CSRS 6622). La note doit enregistrer cette divergence.
    """
    res = _run(
        tp02_lignes_deux_fuseaux,
        Decision("lambert", "choice"),
        qc_profile,
        qc_grid,
        tmp_path,
    )
    data = json.loads(Path(res.journal).read_text(encoding="utf-8"))
    assert data["decision"]["origine"] == "choice"
    assert data["decision"]["note"] == "choix utilisateur ≠ recommandation"
    assert res.fichiers[0].epsg == 6622  # Québec Lambert CSRS


def test_tp27_journal_complet(tp01_points_fuseau7, qc_profile, qc_grid, tmp_path) -> None:
    """TP-27 : structure complète du journal JSON.

    Valide que le journal exporte la structure complète définie en SPEC §8 :
    schema_version, analyse imbriquée, décision, pipeline, fichiers, métadonnées.
    - schema_version au niveau racine et imbriqué (analyse)
    - décision avec origine
    - pipeline_proj non-vide
    - fichiers avec epsg et chemin
    - horodatage et version_outil
    """
    res = _run(
        tp01_points_fuseau7, Decision("recommendation", "auto"), qc_profile, qc_grid, tmp_path
    )
    data = json.loads(Path(res.journal).read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["analyse"]["schema_version"] == 1  # analyse imbriquée (SPEC §8)
    assert data["decision"]["origine"] == "auto"
    assert isinstance(data["pipeline_proj"], list) and data["pipeline_proj"]
    assert data["fichiers"][0]["epsg"] == 2949 and "chemin" in data["fichiers"][0]
    assert "horodatage" in data and data["version_outil"]


def test_split_refuse_ecraser_atomiquement(
    tp02_lignes_deux_fuseaux, qc_profile, qc_grid, tmp_path
) -> None:
    """M1 : la branche split refuse d'écraser AVANT d'écrire quoi que ce soit.

    Une collision sur n'importe quel fichier de zone doit être détectée avant le
    premier write (pré-vérification atomique), pour ne jamais laisser un
    découpage partiel sur le disque.
    """
    extra_zone8 = gpd.GeoDataFrame(
        geometry=[
            LineString([(-74.5, 46.6), (-73.5, 46.6)]),
            LineString([(-74.5, 46.8), (-73.5, 46.8)]),
        ],
        crs=4326,
    )
    couche = gpd.GeoDataFrame(
        pd.concat([tp02_lignes_deux_fuseaux, extra_zone8], ignore_index=True), crs=4326
    )
    d = Decision("split", "choice")
    # Première exécution : succès, deux fichiers de zone écrits.
    _run(couche, d, qc_profile, qc_grid, tmp_path)
    # Deuxième exécution sans overwrite : refus, aucune ré-écriture partielle.
    with pytest.raises(OutputExistsError):
        _run(couche, d, qc_profile, qc_grid, tmp_path)


def test_apply_format_sortie_invalide_leve_valueerror(
    tp01_points_fuseau7, qc_profile, qc_grid, tmp_path
) -> None:
    """DT-06 : un format inconnu via l'API lève ValueError explicite, pas un KeyError brut."""
    with pytest.raises(ValueError, match="xlsx"):
        _run(
            tp01_points_fuseau7,
            Decision("recommendation", "auto"),
            qc_profile,
            qc_grid,
            tmp_path,
            out_format="xlsx",
        )
    assert list(tmp_path.iterdir()) == []  # rien n'a été écrit avant le refus


def test_formats_sortie_invariant_drivers_extensions() -> None:
    """DT-19 : chaque entrée de `_FORMATS` est complète, les extensions ne se
    recouvrent pas (deux formats partageant une extension s'écraseraient au
    découpage), et `FORMATS_GRILLE` est ancrée — contrairement à `FORMATS_SORTIE`
    (déjà pinnée par test_cli_apply_valide_exactement_les_formats_du_noyau), rien
    ne verrouillait encore la disparition silencieuse d'un format de grille."""
    from crs_zone_toolkit import FORMATS_GRILLE
    from crs_zone_toolkit.core.apply import _FORMATS

    for fmt, (driver, ext) in _FORMATS.items():
        assert driver and ext, f"format {fmt} incomplet"
    extensions = [ext for _driver, ext in _FORMATS.values()]
    assert len(extensions) == len(set(extensions)), "deux formats partagent une extension"
    assert FORMATS_GRILLE == ("geojson", "gpkg")


def test_cli_apply_valide_exactement_les_formats_du_noyau() -> None:
    """DT-19 : la validation CLI dérive du noyau — elles ne peuvent plus se désynchroniser."""
    import inspect

    from crs_zone_toolkit import cli
    from crs_zone_toolkit.core.apply import FORMATS_SORTIE

    source = inspect.getsource(cli)
    assert '("gpkg", "geojson", "shp")' not in source, "liste de formats codée en dur dans cli.py"
    assert FORMATS_SORTIE == ("geojson", "gpkg", "shp")


def test_generer_grille_format_invalide_leve_valueerror(tmp_path) -> None:
    """DT-19 : le chemin grid a la même garde que apply (KeyError brut sinon)."""
    import crs_zone_toolkit

    with pytest.raises(ValueError, match="xlsx"):
        crs_zone_toolkit.generate_grid(region="qc", out=tmp_path / "g.xlsx", out_format="xlsx")
    assert not (tmp_path / "g.xlsx").exists()


def test_aide_apply_couvre_formats_sortie() -> None:
    """DT-19 (voie b) : le texte d'aide `--format` d'apply reste littéral (import
    module-level de core.apply évité — coûterait geopandas/pyproj/shapely dès
    `crszone --help`) ; ce test verrouille que chaque format de FORMATS_SORTIE y
    apparaît malgré tout, pour qu'il ne puisse plus dériver silencieusement."""
    import inspect

    from crs_zone_toolkit import cli
    from crs_zone_toolkit.core.apply import FORMATS_SORTIE

    aide = inspect.signature(cli.apply).parameters["out_format"].default.help
    for fmt in FORMATS_SORTIE:
        assert fmt in aide, f"format {fmt} absent du texte d'aide --format d'apply"


def test_aide_grid_couvre_formats_grille() -> None:
    """DT-19 (voie b) : même garantie que ci-dessus pour --format de grid."""
    import inspect

    import crs_zone_toolkit
    from crs_zone_toolkit import cli

    aide = inspect.signature(cli.grid).parameters["out_format"].default.help
    for fmt in crs_zone_toolkit.FORMATS_GRILLE:
        assert fmt in aide, f"format {fmt} absent du texte d'aide --format de grid"
