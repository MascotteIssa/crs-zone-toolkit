"""Verrou du budget de démarrage (finitions revue B, Phase C).

`crszone --help` doit rester ~0,2 s : `geopandas`/`pyproj` ne sont nécessaires
qu'aux commandes (`analyze`/`apply`/`grid`), importées localement dans leurs
corps (DT-19). `affichage.py` importait `target_family` (donc `pyproj`, via
`core/targets.py`) au niveau module — recharge systématique dès `import
crs_zone_toolkit.cli`, y compris pour `--help`, sans qu'aucune commande n'ait
été invoquée. Ce test lance un sous-processus pour observer `sys.modules`
depuis un interpréteur neuf (jamais pollué par un import antérieur du même
process) et DOIT échouer si un import module-niveau de l'une ou l'autre
bibliothèque est réintroduit dans la chaîne d'imports de `cli.py`.
"""

from __future__ import annotations

import subprocess
import sys

_CODE = (
    "import sys\n"
    "import crs_zone_toolkit.cli\n"
    "assert 'geopandas' not in sys.modules, 'geopandas charge au demarrage de la CLI'\n"
    "assert 'pyproj' not in sys.modules, 'pyproj charge au demarrage de la CLI'\n"
)


def test_import_cli_ne_charge_ni_geopandas_ni_pyproj() -> None:
    resultat = subprocess.run([sys.executable, "-c", _CODE], capture_output=True, text=True)
    assert resultat.returncode == 0, resultat.stderr
