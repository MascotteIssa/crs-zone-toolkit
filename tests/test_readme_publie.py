"""Les liens du README, tel qu'il est *publié*.

`pyproject.toml` déclare `readme = "README.md"` : ce fichier n'est pas seulement
la page d'accueil GitHub, il est la `long_description` du paquet — donc la
**page PyPI**. Or PyPI rend ce markdown hors du dépôt, sans base à laquelle
rattacher un chemin : un lien relatif (`docs/SPEC.md`, `LICENSE`) n'y résout
dans aucun cas, il fait 404. Seules les URL absolues survivent aux deux rendus
— et les ancres internes, qui ne sortent pas du document.

Ces tests verrouillent l'invariant : un lien relatif qui réapparaît dans
`README.md` échoue ici, avant d'atteindre PyPI (et une version publiée sur
PyPI ne se dépublie pas).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
README = RACINE / "README.md"
SCRIPT_PUBLIER = RACINE / "scripts" / "publier_release.py"

# Les deux formes d'URL par lesquelles le README pointe DANS le dépôt publié.
# Le `ref` (branche ou tag) n'est pas contraint : ce qui compte ici est le
# chemin visé, seul élément vérifiable sans réseau (SPEC §10).
_DANS_LE_DEPOT = re.compile(
    r"https://(?:github\.com/MascotteIssa/crs-zone-toolkit/blob"
    r"|raw\.githubusercontent\.com/MascotteIssa/crs-zone-toolkit)"
    r"/[^/]+/([^)\s\"]+)"
)

# On ancre sur `](` plutôt que sur le lien entier : cela attrape aussi bien
# `[texte](cible)` et `![alt](cible)` que le badge imbriqué
# `[![alt](image)](cible)`, dont la cible EXTERNE échapperait à un motif qui
# exige un `[` ouvrant (c'est exactement ainsi qu'un lien relatif vers
# `LICENSE` a pu survivre à une première relecture). La cible s'arrête au
# premier blanc : un titre optionnel « (cible "titre") » n'en fait pas partie.
_LIEN_MARKDOWN = re.compile(r"\]\(\s*([^)\s]+)")
# HTML embarqué : le README utilise <picture>/<source srcset>/<img src>.
_LIEN_HTML = re.compile(r'(?:href|src|srcset)="([^"]+)"')

# Ce qui résout aussi bien sur PyPI que sur GitHub.
_PREFIXES_ADMIS = ("https://", "http://", "#", "mailto:")


def _est_publiable(cible: str) -> bool:
    """Vrai si la cible résout dans les DEUX rendus (GitHub et PyPI)."""
    return cible.startswith(_PREFIXES_ADMIS)


def _cibles_du_readme() -> list[tuple[int, str]]:
    """Toutes les cibles de lien du README, avec leur ligne.

    Les blocs de code clôturés sont ignorés : le README y montre des sorties
    console (`crszone analyze …`), et ce qui s'y trouve n'est pas rendu comme
    un lien — le signaler serait un faux positif.
    """
    cibles: list[tuple[int, str]] = []
    dans_un_bloc = False
    for numero, ligne in enumerate(README.read_text(encoding="utf-8").splitlines(), start=1):
        if ligne.lstrip().startswith("```"):
            dans_un_bloc = not dans_un_bloc
            continue
        if dans_un_bloc:
            continue
        for motif in (_LIEN_MARKDOWN, _LIEN_HTML):
            cibles.extend((numero, trouve.group(1)) for trouve in motif.finditer(ligne))
    return cibles


def test_aucun_lien_relatif_dans_le_readme() -> None:
    """Le README publié ne contient que des liens qui résolvent sur PyPI."""
    relatifs = [
        f"ligne {numero} : {cible}"
        for numero, cible in _cibles_du_readme()
        if not _est_publiable(cible)
    ]
    assert relatifs == [], (
        "Liens relatifs dans README.md — ils font 404 sur la page PyPI "
        f'(`readme = "README.md"`) : {relatifs}. Utilise une URL absolue '
        "https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/<chemin> "
        "pour un document à lire rendu, /raw/ pour un fichier à télécharger."
    )


def test_les_ancres_et_les_url_absolues_restent_admises() -> None:
    """Le filtre ne doit pas devenir une chasse au relatif trop zélée : une
    ancre interne fonctionne dans les deux rendus, la convertir en URL serait
    une régression."""
    assert _est_publiable("#la-regle-de-recommandation-en-deux-lignes")
    assert _est_publiable("https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/docs/SPEC.md")
    assert _est_publiable("mailto:imoussahoudou@gmail.com")
    assert not _est_publiable("docs/SPEC.md")
    assert not _est_publiable("LICENSE")
    assert not _est_publiable("./QUICKSTART.md")


def test_l_extraction_voit_bien_les_liens_du_readme() -> None:
    """Garde-fou du garde-fou : si l'extraction cessait de voir les liens (un
    motif cassé, un README vidé), le test précédent passerait à vide sans rien
    prouver. Le README en compte une vingtaine, badges et images compris."""
    cibles = _cibles_du_readme()
    assert len(cibles) >= 20, f"Extraction suspecte : {len(cibles)} lien(s) vu(s) dans README.md."


def _chemins_vises_dans_le_depot() -> list[tuple[int, str]]:
    """Chemins du dépôt visés par les URL du README (`blob/<ref>/…`, `raw/<ref>/…`)."""
    vises = []
    for numero, cible in _cibles_du_readme():
        trouve = _DANS_LE_DEPOT.fullmatch(cible)
        if trouve is not None:
            vises.append((numero, trouve.group(1)))
    return vises


def _perimetre_vitrine() -> tuple:
    import importlib.util

    spec = importlib.util.spec_from_file_location("publier_release", SCRIPT_PUBLIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PERIMETRE_VITRINE, module.fichiers_a_publier


def test_les_liens_du_readme_visent_des_fichiers_reellement_publies() -> None:
    """Une URL du README doit viser un fichier que la vitrine PUBLIE.

    (L'autre moitié — la cible existe vraiment — est le test suivant, gardé au
    dépôt complet : les deux périmètres publiés ne sont pas le même.)

    Les liens sont absolus (test ci-dessus) et pointent sur le dépôt public :
    ils ne résolvent donc que si leur cible y est effectivement publiée. Or le
    périmètre est une liste blanche qui bouge — le 2026-08-22, en sortir sept
    documents techniques aurait laissé le README porter des liens **404 muets**,
    et le couplage n'a été traité qu'à la main, en le remarquant.

    Rien ne l'attrapait : le test précédent ne juge que le caractère *absolu*
    d'un lien, pas l'existence de sa cible ni son appartenance au périmètre. La
    divergence devient ici impossible plutôt que rattrapable (argument DT-19),
    et sans réseau (SPEC §10) : on interroge la liste blanche et l'arbre réel.

    Le `ref` (branche ou tag) n'est pas contraint : épingler un jour les liens
    sur `v0.2.0` ne doit pas faire tomber ce test, qui porte sur le CHEMIN.
    """
    _, fichiers_a_publier = _perimetre_vitrine()
    vises = _chemins_vises_dans_le_depot()
    assert vises, "Aucune URL vers le dépôt trouvée : extraction suspecte."

    hors_perimetre = [
        f"ligne {numero} : {chemin}"
        for numero, chemin in vises
        if fichiers_a_publier([chemin]) != [chemin]
    ]
    assert hors_perimetre == [], (
        "Le README pointe vers des fichiers que la vitrine NE PUBLIE PAS — ces "
        f"liens feront 404 sur GitHub comme sur PyPI : {hors_perimetre}. Soit le "
        "fichier entre dans PERIMETRE_VITRINE (scripts/publier_release.py), soit "
        "le lien sort du README."
    )


@pytest.mark.requiert_depot_git
def test_les_liens_du_readme_visent_des_fichiers_qui_existent() -> None:
    """Second volet : la cible existe vraiment — ce qu'un renommage casserait.

    Séparé du contrôle de périmètre, et **gardé au dépôt complet**, parce que
    les deux périmètres publiés ne sont pas le même : le sdist est
    délibérément plus étroit que la vitrine (ni `docs/images/`, ni
    `exemple_rapport.html` — `pyproject.toml` l'explique). Depuis un sdist
    déplié, l'absence d'un fichier ne prouve donc rien.

    Écrit d'un seul tenant avec le contrôle de périmètre le 2026-08-25, ce test
    confondait les deux et **faisait tomber la suite rejouée depuis le sdist**
    sur les sept images du README. Trouvé par cette rejouabilité même, avant
    toute publication.
    """
    vises = _chemins_vises_dans_le_depot()
    absents = [
        f"ligne {numero} : {chemin}" for numero, chemin in vises if not (RACINE / chemin).is_file()
    ]
    assert absents == [], (
        f"Le README pointe vers des fichiers qui n'existent plus au dépôt : {absents}."
    )
