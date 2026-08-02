"""Phase D — couverture de `scripts/publier_release.py`.

Le périmètre de la vitrine publique est une LISTE BLANCHE : ces tests
verrouillent qu'aucun document interne ne la traverse (la fuite serait
publiée sur GitHub), et que l'essentiel du produit la traverse bien.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "scripts" / "publier_release.py"


def _charger_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("publier_release", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exclut_les_documents_internes() -> None:
    """Aucun document interne ne traverse le filtre — c'est LA raison d'être du script."""
    module = _charger_script()
    internes = [
        "docs/journal_de_bord.md",
        "docs/module_prompt.md",
        "docs/registre_outillage.md",
        "docs/DETTE_TECHNIQUE.md",
        "docs/Definition_Projet_Detection_CRS_Quebec.md",
        "docs/maquette_rapport.html",
        "docs/CO_codes_epsg_quebec.pdf",
        "docs/superpowers/plans/2026-08-01-passe-corrective-suivi.md",
        ".claude/skills/referentiel-crs-quebec/SKILL.md",
        "tests/user_test/PROTOCOLE_TEST_MANUEL.md",
        "tests/user_test/PROTOCOLE_TEST_MANUEL_Archive.md",
    ]
    assert module.fichiers_a_publier(internes) == []


def test_retient_l_essentiel() -> None:
    """Le produit, sa suite, sa CI et ses documents cités traversent le filtre."""
    module = _charger_script()
    essentiels = [
        "README.md",
        "CITATION.cff",
        "pyproject.toml",
        "src/crs_zone_toolkit/cli.py",
        "src/crs_zone_toolkit/regions/qc/profil.toml",
        "tests/test_analysis.py",
        "scripts/regenerer_demos.py",
        ".github/workflows/ci.yml",
        "docs/SPEC.md",
        "docs/calibrage/2026-07-19-calibrage-seuils.md",
        "docs/images/demo.gif",
    ]
    assert module.fichiers_a_publier(essentiels) == essentiels


def test_l_exclusion_prime_sur_la_liste_blanche() -> None:
    """`tests/` est inclus, mais `tests/user_test/` n'en sort pas pour autant."""
    module = _charger_script()
    assert module.fichiers_a_publier(
        ["tests/test_cli.py", "tests/user_test/PROTOCOLE_TEST_MANUEL.md"]
    ) == ["tests/test_cli.py"]


def test_un_fichier_hors_liste_blanche_ne_passe_pas() -> None:
    """Liste blanche stricte : un fichier NOUVEAU au dev ne fuit pas par défaut."""
    module = _charger_script()
    assert module.fichiers_a_publier(["docs/note_interne_quelconque.md"]) == []


def test_vider_cible_preserve_git_dist_et_venv(tmp_path: Path) -> None:
    module = _charger_script()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "ancien.md").write_text("x", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "vieux.md").write_text("x", encoding="utf-8")
    module.vider_cible(tmp_path)
    assert (tmp_path / ".git" / "HEAD").exists()
    assert (tmp_path / "dist").exists()
    assert not (tmp_path / "ancien.md").exists()
    assert not (tmp_path / "docs").exists()


def test_copier_recree_l_arborescence(tmp_path: Path) -> None:
    module = _charger_script()
    source, cible = tmp_path / "source", tmp_path / "cible"
    (source / "docs").mkdir(parents=True)
    (source / "docs" / "SPEC.md").write_text("spec", encoding="utf-8")
    (source / "README.md").write_text("readme", encoding="utf-8")
    cible.mkdir()
    module.copier(source, cible, ["docs/SPEC.md", "README.md"])
    assert (cible / "docs" / "SPEC.md").read_text(encoding="utf-8") == "spec"
    assert (cible / "README.md").read_text(encoding="utf-8") == "readme"
