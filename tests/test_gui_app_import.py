"""Import de gui/app.py — vérifie la classe Api sans jamais ouvrir de fenêtre."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from crs_zone_toolkit.core.errors import MissingCrsError
from crs_zone_toolkit.core.results import Decision
from crs_zone_toolkit.gui import app


def test_api_expose_les_methodes_attendues() -> None:
    for methode in ("pick_file", "pick_folder", "analyze", "apply", "generate_grid", "open_path"):
        assert hasattr(app.Api, methode)


def test_main_existe() -> None:
    assert hasattr(app, "main")


def _ecrire_couche(dossier: Path) -> Path:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = dossier / "couche.geojson"
    gdf.to_file(src, driver="GeoJSON")
    return src


def test_analyze_ecrit_dans_out_dir_pas_a_cote_de_la_source(tmp_path: Path) -> None:
    """Régression : sans dossier de sortie explicite, Api écrivait à côté de la
    source — dangereux quand la source vient d'un dossier en lecture seule."""
    dossier_source = tmp_path / "source"
    dossier_source.mkdir()
    src = _ecrire_couche(dossier_source)
    dossier_sortie = tmp_path / "sortie"
    dossier_sortie.mkdir()

    res = app.Api().analyze(str(src), str(dossier_sortie))

    assert Path(res["report_path"]).parent == dossier_sortie
    assert list(dossier_source.iterdir()) == [src]


def test_apply_ecrit_dans_out_dir_pas_a_cote_de_la_source(tmp_path: Path) -> None:
    dossier_source = tmp_path / "source"
    dossier_source.mkdir()
    src = _ecrire_couche(dossier_source)
    dossier_sortie = tmp_path / "sortie"
    dossier_sortie.mkdir()

    decision = Decision("recommendation", "choice")
    res = app.Api().apply(str(src), decision.choix, str(dossier_sortie))

    assert all(Path(f["chemin"]).parent == dossier_sortie for f in res["fichiers"])
    assert list(dossier_source.iterdir()) == [src]


def test_analyze_sans_crs_leve_missingcrserror_nommee(tmp_path: Path) -> None:
    """G5 (retour utilisateur 24/08) : le JS distingue ce cas par e.name — le
    nom de l'exception Python doit donc rester MissingCrsError."""
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = tmp_path / "sans_crs.shp"
    gdf.to_file(src)
    src.with_suffix(".prj").unlink()

    with pytest.raises(MissingCrsError):
        app.Api().analyze(str(src))


def test_analyze_assume_crs_resout_le_garde_fou(tmp_path: Path) -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = tmp_path / "sans_crs.shp"
    gdf.to_file(src)
    src.with_suffix(".prj").unlink()
    dossier_sortie = tmp_path / "sortie"
    dossier_sortie.mkdir()

    res = app.Api().analyze(str(src), str(dossier_sortie), "EPSG:4326")

    assert res["analysis"]["crs_entree"]["suppose"] is True
    assert Path(res["report_path"]).parent == dossier_sortie


def test_l_ecran_de_selection_ne_promet_pas_de_glisser_deposer() -> None:
    """G3 (25/08) : la zone de dépôt invitait à glisser un fichier sans rien en faire.

    Les gestionnaires posés dans la page ne lisaient jamais `dataTransfer` : le
    cadre se surlignait, le dépôt restait sans effet, et l'utilisateur l'a
    constaté au test. Le geste a été retiré plutôt que branché, pour une raison
    qui tient au domaine : une couche Shapefile est un jeu de fichiers
    solidaires (`.shp`, `.shx`, `.dbf`, `.prj`), que déposer un fichier unique
    représente mal. Ce test interdit que la promesse revienne sans le geste.
    """
    page = (Path(app.__file__).parent / "web" / "index.html").read_text(encoding="utf-8")
    assert "Glissez" not in page
    for evenement in ("dragenter", "dragover", "dragleave", "dataTransfer"):
        assert evenement not in page, f"gestionnaire de glisser-déposer revenu : {evenement}"


def test_l_ecran_de_recommandation_montre_les_trois_statistiques_de_distorsion() -> None:
    """G3 (25/08) : l'écran n'affichait qu'un chiffre, la moyenne, sans la nommer.

    Le motif de la recommandation cite le maximum, et la décision se prend sur
    `max(|min|, |max|)` (`core/messages.py`, tableau `min / moy / max` du
    terminal). Montrer la seule moyenne, sans étiquette, donnait donc à l'écran
    un chiffre qui n'était ni celui du motif ni celui qui tranche. Le repère
    était en plus positionné sur `|moyenne|`, ce qui collait deux candidats de
    gravité très différente au même bout de la barre.
    """
    page = (Path(app.__file__).parent / "web" / "index.html").read_text(encoding="utf-8")
    for statistique in ("min_ppm", "moy_ppm", "max_ppm"):
        assert statistique in page, f"l'écran n'affiche plus {statistique}"
    assert "Math.abs(d.moy_ppm) / (seuil" not in page, "le repère suit encore la moyenne"
