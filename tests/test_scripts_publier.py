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

import pytest

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


def _source_renommee_en(module: ModuleType, destination: str) -> str:
    """Le chemin dev publié SOUS `destination` dans la vitrine (table de renommage)."""
    sources = [s for s, d in module.RENOMMAGES_VITRINE if d == destination]
    assert len(sources) == 1, f"Une seule source attendue pour {destination!r}, trouvé : {sources}"
    return sources[0]


def _gitignore_a_controler(module: ModuleType) -> Path | None:
    """Le `.gitignore` destiné au public, où qu'on exécute la suite.

    Au dépôt de développement, c'est la SOURCE renommée à la copie. Dans la
    vitrine (et dans le sdist déplié), cette source n'est pas publiée : ce qui
    existe, c'est le `.gitignore` déjà produit. Viser l'un ou l'autre garde le
    contrôle vrai des deux côtés, et le rend même plus fort à la vitrine
    puisqu'il porte alors sur l'artefact réellement livré.

    Rend `None` dans le sdist déplié, qui ne transporte ni l'outillage de
    publication ni les métadonnées git : il n'y a alors rien à contrôler.
    """
    source = RACINE / _source_renommee_en(module, ".gitignore")
    if source.is_file():
        return source
    publie = RACINE / ".gitignore"
    return publie if publie.is_file() else None


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
    """Aucun document interne ne traverse le filtre — c'est LA raison d'être du script.

    Ce fichier de test est lui-même publié (vitrine ET sdist PyPI) : il ne doit
    donc pas servir de sommaire des documents internes. Deux régimes, selon ce
    qui porte la valeur de preuve — `_correspond` est purement lexical : il
    compare un chemin EXACT hors liste blanche, ou un PRÉFIXE de dossier :

    - le chemin EST le fichier réel à protéger (`docs/journal_de_bord.md`, …) :
      il reste tel quel, c'est lui la preuve, et son nom est de toute façon
      inévitable dès qu'on veut prouver qu'il ne sort pas ;
    - la preuve tient à la MÉCANIQUE (un dossier entier hors liste blanche) :
      des chemins génériques suffisent, puisque le filtre ne connaît de toute
      façon aucun de ces dossiers. Les nommer n'ajouterait rien au test.

    Ne remplacez pas les chemins génériques par des chemins réels : la preuve
    serait identique, la fuite gratuite.
    """
    module = _charger_script()
    internes = [
        "docs/journal_de_bord.md",
        "docs/module_prompt.md",
        "docs/registre_outillage.md",
        "docs/DETTE_TECHNIQUE.md",
        "docs/Definition_Projet_Detection_CRS_Quebec.md",
        "docs/maquette_rapport.html",
        "docs/CO_codes_epsg_quebec.pdf",
        "docs/notes_internes/plans/un-plan-interne.md",
        "outils_internes/config/reglage.md",
        "tests/user_test/PROTOCOLE_TEST_MANUEL.md",
        "tests/user_test/PROTOCOLE_TEST_MANUEL_Archive.md",
    ]
    assert module.fichiers_a_publier(internes) == []


# Vocabulaire AUTORISÉ du `.gitignore` publié. Liste blanche, comme le périmètre
# lui-même : une règle qui ne figure pas ici ne part pas dans la vitrine. Un
# dépôt de développement ignore forcément d'autres choses (réglages du poste,
# dossiers de travail) — sans intérêt pour un contributeur externe, et `.gitignore`
# est un des premiers fichiers qu'il ouvrira. Élargir ce fichier suppose donc
# d'élargir cette liste, c'est-à-dire de le décider explicitement.
MOTIFS_AUTORISES_GITIGNORE: frozenset[str] = frozenset(
    {
        ".venv/",
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
        ".ruff_cache/",
        ".mypy_cache/",
        ".coverage",
        "htmlcov/",
        "dist/",
        "build/",
        "*.egg-info/",
        "sorties/",
        "*_analyse_crs*.html",
        "*_journal.json",
        ".vscode/",
        ".idea/",
        "Thumbs.db",
        ".DS_Store",
    }
)

# Les commentaires aussi sont lus : ils sont titrés, et la liste des titres est
# fermée (une section nouvelle est une décision, pas un effet de bord).
SECTIONS_AUTORISEES_GITIGNORE: frozenset[str] = frozenset(
    {
        "# Environnements et caches Python",
        "# Build / distribution",
        "# Sorties de l'outil pendant les essais",
        "# IDE / OS",
    }
)


def test_le_gitignore_publie_n_ecrit_que_du_vocabulaire_autorise() -> None:
    """Le `.gitignore` de la vitrine ne dit QUE ce qu'un contributeur rencontre.

    Celui du dépôt de développement ne peut pas être purgé (sans ses règles,
    l'outillage du poste finirait committé) : la vitrine reçoit donc le sien,
    publié par renommage à la copie. Ce test le tient au vocabulaire décidé.
    """
    module = _charger_script()
    fichier = _gitignore_a_controler(module)
    if fichier is None:
        pytest.skip("sdist déplié : ni outillage de publication, ni .gitignore à contrôler.")
    lignes = [ligne.strip() for ligne in fichier.read_text(encoding="utf-8").splitlines()]
    hors_vocabulaire = [
        ligne
        for ligne in lignes
        if ligne
        and ligne not in MOTIFS_AUTORISES_GITIGNORE
        and ligne not in SECTIONS_AUTORISEES_GITIGNORE
    ]
    assert hors_vocabulaire == [], (
        f"Lignes hors liste blanche dans le `.gitignore` publié : {hors_vocabulaire}. "
        "Soit elles appartiennent au `.gitignore` du dépôt dev, soit il faut les "
        "ajouter ici — délibérément."
    )


def test_le_gitignore_du_dev_ne_traverse_pas_le_filtre() -> None:
    """Il est remplacé, pas recopié : hors liste blanche, donc jamais publié tel quel."""
    module = _charger_script()
    assert ".gitignore" not in module.PERIMETRE_VITRINE
    assert module.fichiers_a_publier([".gitignore"]) == []


def test_le_gitignore_de_la_vitrine_traverse_le_filtre_sous_son_nom_final() -> None:
    """Une source renommée est publiée (liste blanche) et change de nom à la copie."""
    module = _charger_script()
    source = _source_renommee_en(module, ".gitignore")
    assert module.fichiers_a_publier([source]) == [source]
    assert module.destination_vitrine(source) == ".gitignore"
    assert module.destination_vitrine("README.md") == "README.md"


def test_copier_renomme_a_la_copie(tmp_path: Path) -> None:
    """Le mécanisme lui-même : la source arrive dans la cible sous son nom final."""
    module = _charger_script()
    source_dir, cible = tmp_path / "source", tmp_path / "cible"
    chemin = _source_renommee_en(module, ".gitignore")
    (source_dir / chemin).parent.mkdir(parents=True)
    (source_dir / chemin).write_text("dist/\n", encoding="utf-8")
    cible.mkdir()

    module.copier(source_dir, cible, [chemin])

    assert (cible / ".gitignore").read_text(encoding="utf-8") == "dist/\n"
    assert not (cible / chemin).exists()


def test_le_gitignore_publie_couvre_l_essentiel_d_un_contributeur() -> None:
    """Utile, pas seulement inoffensif : caches Python, build et sorties de l'outil."""
    module = _charger_script()
    fichier = _gitignore_a_controler(module)
    if fichier is None:
        pytest.skip("sdist déplié : ni outillage de publication, ni .gitignore à contrôler.")
    contenu = fichier.read_text(encoding="utf-8")
    for motif in (".venv/", "__pycache__/", "dist/", "build/", "*.egg-info/", "sorties/"):
        assert motif in contenu, f"{motif} absent du `.gitignore` de la vitrine."


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
