"""Test de fumée : le package s'importe et expose sa version.

Garde-fou multi-plateforme (Ubuntu/Windows × Python 3.11–3.13) contre les
erreurs d'import de la stack géospatiale, et garantit qu'au moins un test est
collecté sur le squelette (CI verte). Les vrais cas TP-xx arrivent en TDD.
"""

import re
from pathlib import Path

import crs_zone_toolkit


def test_le_package_expose_une_version() -> None:
    """La forme, pas le numéro.

    Ce test épinglait `"0.1.0"` en dur : il fallait l'éditer à chaque release,
    et il ne prouvait rien qu'un lecteur de `__init__.py` ne voie déjà.
    `__version__` est la source unique (pyproject la lit, la CLI et le rapport
    l'estampillent) ; ce qui mérite un test, c'est qu'elle reste lisible par
    ces trois consommateurs.
    """
    assert re.fullmatch(r"\d+\.\d+\.\d+", crs_zone_toolkit.__version__)


def test_citation_cff_annonce_la_version_du_paquet() -> None:
    """La notice de citation ne doit pas dériver du paquet.

    Elle l'a déjà fait : `CITATION.cff` portait `version: 0.1.0` daté du
    2026-08-02 alors que la release publiée l'avait été le 15/08. Un lecteur
    qui cite l'outil recopie ce fichier, jamais `__init__.py` — une version
    fausse s'y propage dans des bibliographies qu'on ne rattrape plus.
    """
    cff = Path(__file__).resolve().parent.parent / "CITATION.cff"
    declaree = re.search(r"^version:\s*(\S+)$", cff.read_text(encoding="utf-8"), re.M)
    assert declaree is not None, "CITATION.cff ne déclare aucune version"
    assert declaree.group(1) == crs_zone_toolkit.__version__
