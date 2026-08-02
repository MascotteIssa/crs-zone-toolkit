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

README = Path(__file__).resolve().parent.parent / "README.md"

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
