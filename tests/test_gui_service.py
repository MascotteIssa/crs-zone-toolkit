"""Façade gui/service.py — fonctions pures, sans pywebview, appelées par gui/app.py."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from crs_zone_toolkit.core.results import Decision
from crs_zone_toolkit.gui import service


def _ecrire_couche(tmp_path: Path) -> Path:
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.7, 45.5)], crs=4326)
    src = tmp_path / "couche.geojson"
    gdf.to_file(src, driver="GeoJSON")
    return src


def test_run_analyze(tmp_path: Path) -> None:
    src = _ecrire_couche(tmp_path)
    result = service.run_analyze(src)
    assert result.schema_version == 1


def test_run_report(tmp_path: Path) -> None:
    src = _ecrire_couche(tmp_path)
    rapport = service.run_report(src, out_dir=tmp_path)
    assert rapport.exists()


def test_run_report_assume_crs_sur_couche_sans_crs(tmp_path: Path) -> None:
    """G5 (retour utilisateur 24/08) : le rapport doit pouvoir se régénérer avec
    le CRS assigné après le garde-fou MissingCrsError, pas seulement l'analyse."""
    gdf = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4)], crs=4326)
    src = tmp_path / "sans_crs.shp"
    gdf.to_file(src)
    src.with_suffix(".prj").unlink()  # supprime la déclaration de CRS

    rapport = service.run_report(src, out_dir=tmp_path, assume_crs="EPSG:4326")

    assert rapport.exists()


@pytest.mark.parametrize(
    ("choice", "attendu"),
    [
        ("recommendation", Decision("recommendation", "choice")),
        ("lambert", Decision("lambert", "choice")),
        ("split", Decision("split", "choice")),
    ],
)
def test_decision_from_choice(choice: str, attendu: Decision) -> None:
    assert service.decision_from_choice(choice) == attendu


def test_decision_from_choice_valeur_invalide() -> None:
    with pytest.raises(ValueError, match="autre_chose"):
        service.decision_from_choice("autre_chose")


def test_run_apply(tmp_path: Path) -> None:
    src = _ecrire_couche(tmp_path)
    decision = service.decision_from_choice("recommendation")
    result = service.run_apply(src, decision, out_dir=tmp_path)
    assert len(result.fichiers) >= 1


def test_run_generate_grid(tmp_path: Path) -> None:
    out = tmp_path / "grille.geojson"
    chemin, n, attributs = service.run_generate_grid(out=out)
    assert chemin.exists()
    assert n > 0
    assert attributs == (
        "zone",
        "epsg_csrs",
        "epsg_nad83",
        "epsg_nad27",
        "meridien_central",
        "lon_min",
        "lon_max",
    )


def test_run_apply_decoupage_produit_les_memes_sorties_que_la_cli(
    tp02bis_deux_fuseaux_majoritaires, tmp_path: Path
) -> None:
    """La façade de l'interface découpe vraiment, comme `[3]` au menu et `--choice split`.

    Trou de couverture de la même famille que DT-08, sur la troisième surface :
    `decision_from_choice("split")` était testé, mais aucun test ne faisait
    traverser `run_apply` par une décision de découpage — la façade pouvait
    annoncer un découpage à la page et livrer un seul fichier reprojeté.

    La couche est la fixture partagée `tp02bis_deux_fuseaux_majoritaires`, celle
    dont le noyau (`test_analysis_alternative_split.py`) et la maquette `CLI_UX`
    §3 se servent déjà : deux fuseaux majoritaires, donc deux fichiers. Aucune
    géométrie n'est redéfinie ici, sans quoi l'égalité entre surfaces serait une
    coïncidence plutôt qu'une preuve.

    Morsure : faire ignorer `decision` à `service.run_apply` (décision figée sur
    `recommendation`) rend un seul fichier et fait tomber ce test.
    """
    src = tmp_path / "lignes.geojson"
    tp02bis_deux_fuseaux_majoritaires.to_file(src, driver="GeoJSON")

    result = service.run_apply(src, service.decision_from_choice("split"), out_dir=tmp_path)

    produits = sorted(tmp_path.glob("lignes_zone*_epsg*.gpkg"))
    assert len(produits) == 2
    assert len(result.fichiers) == len(produits)
    total = sum(len(gpd.read_file(p)) for p in produits)
    assert total == len(tp02bis_deux_fuseaux_majoritaires)  # aucune coupée, aucune dupliquée
