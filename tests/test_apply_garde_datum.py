"""Garde de transformation de datum : refuser ou avertir (DT-01, DATA_REFERENCE §6.1).

Le point de décision est une fonction PURE : ces tests sont déterministes et ne
dépendent d'AUCUNE grille PROJ installée sur la machine (leçon de J5 : un test
qui dépend d'une grille est vert en local et rouge en CI).
"""

import pytest

from crs_zone_toolkit.core.apply import _exige_transformation_exacte

# (famille_source, famille_cible, familles_obligatoires, attendu)
CAS = [
    # NAD27 impliqué → transformation exacte obligatoire (écarts en dizaines de mètres)
    ("nad27", "csrs", ("nad27",), True),
    ("csrs", "nad27", ("nad27",), True),
    ("nad27", "nad27", ("nad27",), True),
    # Familles modernes entre elles → repli acceptable (écart mesuré nul à décimétrique)
    ("csrs", "csrs", ("nad27",), False),
    ("wgs84", "csrs", ("nad27",), False),
    ("nad83", "nad83", ("nad27",), False),
    ("nad83", "csrs", ("nad27",), False),
    # Profil ne déclarant aucune famille à risque → jamais d'exigence
    ("nad27", "csrs", (), False),
    # Profil déclarant plusieurs familles
    ("nad83", "csrs", ("nad27", "nad83"), True),
]


@pytest.mark.parametrize(("source", "cible", "obligatoires", "attendu"), CAS)
def test_exige_transformation_exacte(source, cible, obligatoires, attendu):
    assert _exige_transformation_exacte(source, cible, obligatoires) is attendu


# ── Intégration : insensible à l'environnement ─────────────────────────────
# Avec la grille CSRS v2 : chemin exact. Sans elle : repli accepté. Dans les
# DEUX cas le fichier doit être produit — l'assertion ne dépend donc d'aucune
# grille installée. L'avertissement, lui, N'EST PAS asserté ici : sa présence
# dépend justement de l'environnement (leçon de J5).


def test_lambert_sexecute_avec_ou_sans_grille(tmp_path):
    """DT-01 : la recommandation Lambert (6622, datum CSRS v2) doit s'exécuter.

    Auparavant : TransformUnavailableError chez quiconque n'a pas
    ca_nrc_NA83SCRS.tif — l'outil refusait ce qu'il venait de recommander.
    """
    import geopandas as gpd
    from shapely.geometry import LineString

    import crs_zone_toolkit
    from crs_zone_toolkit.core.results import Decision

    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    gdf = gpd.GeoDataFrame(geometry=lignes, crs=4326)  # WGS84, deux fuseaux
    src = tmp_path / "routes.geojson"
    gdf.to_file(src, driver="GeoJSON")

    res = crs_zone_toolkit.apply(src, Decision("lambert", "choice"), out_dir=tmp_path)

    from pathlib import Path

    assert res.fichiers[0].epsg == 6622
    assert Path(res.fichiers[0].chemin).exists()
    assert Path(res.journal).exists()
