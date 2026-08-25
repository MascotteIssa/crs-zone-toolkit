"""La « commande de reproduction » du rapport doit RÉELLEMENT s'exécuter.

Défaut corrigé : chaque rapport affichait `crszone analyze <nom> --region qc`.
Doublement faux — `--region` est une option GLOBALE (elle se place AVANT la
sous-commande, `docs/CLI_UX.md` §11), et `<nom>` était le nom de couche SANS
extension, donc le fichier n'existait pas. Un lecteur qui recopiait la ligne
tombait sur `No such option: --region`.

Ces tests ne relisent pas la chaîne attendue : ils EXÉCUTENT la commande que
le rapport affiche. Tant qu'ils passent, la ligne imprimée est reproductible.
"""

from __future__ import annotations

import importlib.util
import re
import shlex
import subprocess
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point
from typer.testing import CliRunner

import crs_zone_toolkit
from crs_zone_toolkit.cli import app

runner = CliRunner()

RACINE = Path(__file__).resolve().parent.parent

_REPRO = re.compile(r'<div class="repro">.*?<b>(?P<commande>.*?)</b>', re.S)

# `crszone <sous-commande> … --region` : l'option globale placée APRÈS la
# sous-commande. Typer refuse (`No such option: --region`).
_REGION_MAL_PLACEE = re.compile(r"crszone\s+(?:analyze|apply|grid)\b[^\n`]*--region")

_DOCUMENTS_PUBLIES = (".md", ".html", ".j2")


def _couche(dossier: Path, nom: str = "ma_couche.geojson") -> Path:
    chemin = dossier / nom
    points = gpd.GeoDataFrame(geometry=[Point(-71.9, 45.4), Point(-71.8, 45.5)], crs=4326)
    points.to_file(chemin, driver="GeoJSON")
    return chemin


def _commande_affichee(html: str) -> str:
    trouve = _REPRO.search(html)
    assert trouve is not None, "Aucun bloc `repro` dans le rapport."
    return trouve.group("commande").strip()


@pytest.fixture
def commande(tmp_path: Path) -> str:
    """La commande de reproduction telle qu'un lecteur la voit dans son rapport."""
    source = _couche(tmp_path)
    rapport = crs_zone_toolkit.report(source, region="qc", out_dir=tmp_path)
    return _commande_affichee(rapport.read_text(encoding="utf-8"))


def test_la_commande_place_region_avant_la_sous_commande(commande: str) -> None:
    """`--region` est globale : après `analyze`, Typer répond `No such option`."""
    jetons = shlex.split(commande)
    assert jetons[0] == "crszone"
    assert jetons.index("--region") < jetons.index("analyze"), commande


def test_la_commande_nomme_un_fichier_avec_son_extension(commande: str) -> None:
    """Le nom de couche du rapport est un radical (`ma_couche`) : sans
    extension, la commande échoue sur un fichier inexistant."""
    fichier = shlex.split(commande)[-1]
    assert fichier == "ma_couche.geojson", commande


def test_la_commande_affichee_s_execute_vraiment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La preuve : on rejoue la ligne imprimée, telle quelle, et elle sort en 0."""
    source = _couche(tmp_path)
    rapport = crs_zone_toolkit.report(source, region="qc", out_dir=tmp_path)
    commande = _commande_affichee(rapport.read_text(encoding="utf-8"))

    jetons = shlex.split(commande)
    assert jetons[0] == "crszone"
    monkeypatch.chdir(tmp_path)  # le rapport nomme la couche sans chemin
    resultat = runner.invoke(app, jetons[1:])

    assert resultat.exit_code == 0, f"{commande} → code {resultat.exit_code}\n{resultat.output}"


def _documents_publies() -> list[Path]:
    """Les documents (`.md`, `.html`, `.j2`) du périmètre public, et eux seuls.

    La liste vient de `scripts/publier_release.py` : elle suit le périmètre
    sans qu'on ait à la maintenir ici en double.
    """
    spec = importlib.util.spec_from_file_location(
        "publier_release", RACINE / "scripts" / "publier_release.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suivis = subprocess.run(
        ["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [
        RACINE / f
        for f in module.fichiers_a_publier(ligne for ligne in suivis if ligne)
        if f.endswith(_DOCUMENTS_PUBLIES)
    ]


@pytest.mark.requiert_depot_git
def test_aucun_document_publie_ne_montre_region_apres_la_sous_commande() -> None:
    """Même défaut, autre support : synopsis de la SPEC, extrait du README,
    rapport d'exemple. `docs/CLI_UX.md` §9 fait foi — `--region` est globale."""
    fautifs = [
        f"{chemin.relative_to(RACINE).as_posix()}:{n}: {ligne.strip()[:120]}"
        for chemin in _documents_publies()
        for n, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1)
        if _REGION_MAL_PLACEE.search(ligne)
    ]
    assert fautifs == [], "`--region` se place AVANT la sous-commande :\n" + "\n".join(fautifs)
