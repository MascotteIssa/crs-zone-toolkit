"""Test de fumée : le package s'importe et expose sa version.

Garde-fou multi-plateforme (Ubuntu/Windows × Python 3.11–3.13) contre les
erreurs d'import de la stack géospatiale, et garantit qu'au moins un test est
collecté sur le squelette (CI verte). Les vrais cas TP-xx arrivent en TDD.
"""

import crs_zone_toolkit


def test_le_package_expose_une_version() -> None:
    assert crs_zone_toolkit.__version__ == "0.1.0"
