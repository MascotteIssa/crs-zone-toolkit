"""Phase D — couverture de `scripts/publier_release.py`.

Le périmètre de la vitrine publique est une LISTE BLANCHE : ces tests
verrouillent qu'aucun document interne ne la traverse (la fuite serait
publiée sur GitHub), et que l'essentiel du produit la traverse bien.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "scripts" / "publier_release.py"
PYPROJECT = RACINE / "pyproject.toml"


def _charger_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("publier_release", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_publier_cp1252(cible: Path) -> subprocess.CompletedProcess[bytes]:
    """Lance le script en sous-processus dont la console est cp1252 (même
    reproduction que DT-15 / `tests/test_cli_encodage.py`) — la console
    Windows par défaut sans redirection UTF-8 explicite."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--cible", str(cible)],
        capture_output=True,
        env=env,
    )


def _sdist() -> dict[str, list[str]]:
    """Le bloc `[tool.hatch.build.targets.sdist]` tel que le build le lira."""
    with PYPROJECT.open("rb") as flux:
        return tomllib.load(flux)["tool"]["hatch"]["build"]["targets"]["sdist"]


def _normaliser(entree: str) -> str:
    """`/docs/calibrage` (écriture hatch) et `docs/calibrage/` (écriture
    vitrine) désignent la même chose : on ramène les deux à `docs/calibrage`."""
    return entree.strip("/")


def _couvert_par(entree: str, perimetre: tuple[str, ...]) -> bool:
    """Vrai si `entree` (du sdist) tombe dans une entrée de la liste blanche
    vitrine — soit à l'identique, soit sous un de ses dossiers."""
    cible = _normaliser(entree)
    return any(cible == _normaliser(v) or cible.startswith(_normaliser(v) + "/") for v in perimetre)


def test_le_perimetre_du_sdist_est_inclus_dans_celui_de_la_vitrine() -> None:
    """DT-19 — rendre la divergence IMPOSSIBLE, pas seulement improbable.

    Les deux publications doivent avoir le même périmètre : ce qui ne sort pas
    sur GitHub ne sort pas non plus sur PyPI. La vitrine est une liste blanche ;
    le sdist doit l'être aussi, et rester INCLUS dedans (il est délibérément
    plus étroit : ni `docs/images/`, ni `docs/exemple_rapport.html`). Une
    inclusion en bloc du type `/docs` rouvrirait la fuite — et une version
    publiée sur PyPI ne se dépublie pas.
    """
    module = _charger_script()
    non_couverts = [e for e in _sdist()["include"] if not _couvert_par(e, module.PERIMETRE_VITRINE)]
    assert non_couverts == [], (
        f"Entrées de l'`include` du sdist absentes de PERIMETRE_VITRINE : {non_couverts}. "
        "Ajoute-les à la vitrine, ou restreins le sdist."
    )


def test_le_sdist_garde_l_exclusion_residuelle_du_protocole_de_test() -> None:
    """`/tests` entre en bloc dans le sdist (la suite doit pouvoir être rejouée) :
    sans cette exclusion, les protocoles internes de `tests/user_test/`
    repartiraient vers PyPI. C'est le pendant exact de EXCLUSIONS_VITRINE."""
    module = _charger_script()
    assert "/tests/user_test/**" in _sdist()["exclude"]
    assert "tests/user_test/" in module.EXCLUSIONS_VITRINE


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


def test_dt15_forcer_utf8_reconfigure_les_flux(monkeypatch) -> None:
    """Même contrat que `crs_zone_toolkit.cli._forcer_utf8` (DT-15) : un flux
    cp1252 reconfigurable ressort en UTF-8, prêt à écrire « ✓ » sans planter."""
    module = _charger_script()
    brut_out = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(brut_out, encoding="cp1252"))

    module._forcer_utf8()

    assert sys.stdout.encoding.lower() == "utf-8"
    sys.stdout.write("✓ copié")
    sys.stdout.flush()
    assert brut_out.getvalue().decode("utf-8") == "✓ copié"


def test_dt15_publier_sous_cp1252_sort_en_utf8_avec_message_final(tmp_path: Path) -> None:
    """Le défaut reproduit : sous une console cp1252 (défaut Windows sans
    redirection UTF-8 explicite), le script copiait bien les fichiers puis
    plantait (`UnicodeEncodeError`) sur son dernier `print` — code de sortie 1,
    et la consigne finale (« Reste manuel… ») n'était jamais affichée alors que
    c'est justement ce dont le mainteneur a besoin pour terminer la publication."""
    cible = tmp_path / "cible"
    cible.mkdir()
    (cible / ".git").mkdir()

    resultat = _run_publier_cp1252(cible)

    assert resultat.returncode == 0, resultat.stderr.decode("cp1252", errors="replace")
    sortie = resultat.stdout.decode("utf-8")
    assert "✓" in sortie
    assert "fichiers copiés" in sortie
    assert "Reste manuel, dans le clone cible" in sortie
