"""Prépare le snapshot « vitrine » du dépôt public `crs-zone-toolkit` (Phase D).

Le projet vit dans DEUX dépôts (décision du 2026-07-27) :
- `crs-zone-toolkit-dev` (privé) : historique complet, journal, outillage ;
- `crs-zone-toolkit` (public) : la « vitrine », snapshot curé à historique neuf.

La vitrine ne s'édite JAMAIS à la main : toute correction se fait au dépôt dev,
puis se republie en relançant ce script. Le périmètre est une LISTE BLANCHE
explicite — un fichier nouveau au dev n'entre dans la vitrine que si on
l'ajoute ici. La fuite d'un document interne est ainsi impossible par
construction (même principe que DT-19 : rendre la dérive impossible plutôt que
la rattraper). Le périmètre du sdist (`pyproject.toml`) est aligné sur cette
liste : ce qui ne sort pas sur GitHub ne sort pas sur PyPI. Une seconde table
(`RENOMMAGES_VITRINE`) publie un fichier sous un AUTRE nom — le `.gitignore`,
que les deux dépôts n'écrivent pas pareil.

Usage :
    uv run python scripts/publier_release.py --cible ../crs_zone_toolkit_vitrine

Le script COPIE puis s'arrête : la revue du statut git, le commit et le push
restent des gestes manuels dans le clone cible (l'utilisateur est seul auteur).
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def _forcer_utf8() -> None:
    """Force l'UTF-8 sur stdout/stderr (même correctif que `cli.py`, DT-15).
    Sans ça, une console Windows non redirigée en UTF-8 retombe sur cp1252 :
    les « ✓ »/« ✗ »/« ⚠ » de ce script plantent (UnicodeEncodeError) après
    coup — le script a déjà fait son travail (copie réussie) mais sort en
    échec sans jamais afficher la consigne finale. Les flux de test/capture
    qui n'exposent pas ``reconfigure`` sont laissés intacts."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue
        with contextlib.suppress(ValueError, OSError):  # flux déjà engagé / non reconfigurable
            reconfigurer(encoding="utf-8")


# Liste blanche : entrée finissant par « / » = préfixe (dossier), sinon chemin
# exact. Toute évolution du périmètre public passe par une modification ICI,
# relue et committée — jamais par un effet de bord.
PERIMETRE_VITRINE: tuple[str, ...] = (
    ".gitattributes",
    ".github/",
    ".pre-commit-config.yaml",
    "CITATION.cff",
    "LICENSE",
    "QUICKSTART.md",
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/CLI_UX.md",
    "docs/DATA_REFERENCE.md",
    "docs/SPEC.md",
    "docs/TEST_PLAN.md",
    "docs/calibrage/",
    "docs/exemple_rapport.html",
    "docs/feuille_de_route.md",
    "docs/images/",
    "docs/references.md",
    "pyproject.toml",
    "scripts/",
    "src/",
    "tests/",
    "uv.lock",
)

# Fichiers publiés SOUS UN AUTRE NOM (source au dev → destination à la vitrine).
# Un fichier de cette table est publié comme s'il était en liste blanche.
#
# `.gitignore` : les deux dépôts n'ignorent pas les mêmes choses. Celui du dev
# doit couvrir l'outillage local du poste (sans quoi il finirait committé), et
# ces règles nomment des dossiers de travail qui n'existent pas dans la vitrine
# — or `.gitignore` est un des premiers fichiers qu'un lecteur ouvre. La vitrine
# reçoit donc le sien, qui ne parle que de ce qu'un contributeur externe
# rencontre : environnements, build, IDE, sorties de l'outil.
RENOMMAGES_VITRINE: tuple[tuple[str, str], ...] = (("packaging/gitignore-vitrine", ".gitignore"),)

_DESTINATIONS: dict[str, str] = dict(RENOMMAGES_VITRINE)

# Exclusions APRÈS liste blanche : le protocole de test manuel vit sous
# `tests/`, qui est inclus, mais reste interne (il référence des données
# git-ignorées qu'un lecteur public n'aura jamais).
EXCLUSIONS_VITRINE: tuple[str, ...] = ("tests/user_test/",)

# Ce qu'on ne détruit jamais dans le clone cible.
CONSERVES_CIBLE: tuple[str, ...] = (".git", "dist", ".venv")


def _correspond(fichier: str, entrees: tuple[str, ...]) -> bool:
    return any(fichier.startswith(e) if e.endswith("/") else fichier == e for e in entrees)


def fichiers_a_publier(fichiers_suivis: Iterable[str]) -> list[str]:
    """Filtre pur : liste blanche (+ sources renommées), moins les exclusions.

    Rend des chemins SOURCE, tels qu'ils existent au dev ; leur nom dans la
    vitrine se lit avec `destination_vitrine`. Testable sans git.
    """
    return [
        f
        for f in fichiers_suivis
        if not _correspond(f, EXCLUSIONS_VITRINE)
        and (_correspond(f, PERIMETRE_VITRINE) or f in _DESTINATIONS)
    ]


def destination_vitrine(fichier: str) -> str:
    """Nom du fichier DANS la vitrine : renommage s'il est tabulé, sinon identité."""
    return _DESTINATIONS.get(fichier, fichier)


def vider_cible(cible: Path) -> None:
    """Vide le clone cible, sauf `.git/` (l'historique vitrine), `dist/`, `.venv/`."""
    for enfant in cible.iterdir():
        if enfant.name in CONSERVES_CIBLE:
            continue
        if enfant.is_dir():
            shutil.rmtree(enfant)
        else:
            enfant.unlink()


def copier(racine: Path, cible: Path, fichiers: list[str]) -> None:
    for f in fichiers:
        destination = cible / destination_vitrine(f)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(racine / f, destination)


def main() -> int:
    _forcer_utf8()  # DT-15 : avant toute sortie, indépendamment du codepage console
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument(
        "--cible",
        type=Path,
        required=True,
        help="clone local du dépôt vitrine (doit contenir un .git)",
    )
    arguments = parseur.parse_args()
    cible: Path = arguments.cible.resolve()
    if not (cible / ".git").is_dir():
        print(f"✗ {cible} n'est pas un clone git — on ne vide pas un dossier arbitraire.")
        return 2
    statut = subprocess.run(
        ["git", "status", "--porcelain"], cwd=RACINE, capture_output=True, text=True, check=True
    )
    if statut.stdout.strip():
        print("⚠ Le dépôt dev a des changements non committés : le snapshot les inclura.")
    suivis = subprocess.run(
        ["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    retenus = fichiers_a_publier([ligne for ligne in suivis if ligne])
    vider_cible(cible)
    copier(RACINE, cible, retenus)
    print(f"✓ {len(retenus)} fichiers copiés vers {cible} ({len(suivis)} suivis au dev).")
    print("  Reste manuel, dans le clone cible : git status (revue), commit, tag, push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
