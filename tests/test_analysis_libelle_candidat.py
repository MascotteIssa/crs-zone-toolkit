"""DT-20 (1) — le suffixe « (tout) » du candidat dominant (maquette CLI_UX §3).

Maquette : `MTM fuseau 9 (tout)` ; code : `MTM fuseau 8`. **Arbitré : le code
rejoint la maquette**, mais le suffixe ne s'affiche **que si ≥ 2 fuseaux sont
traversés** — sur une couche mono-fuseau il serait du bruit.

Ce que le suffixe dit, et pourquoi il compte : la distorsion du candidat
« fuseau » est mesurée sur **toute** la couche, y compris ses parts situées
**hors de ce fuseau** — par opposition au découpage, où chaque morceau serait
mesuré dans son propre fuseau. Sans lui, un chiffre comme 14 784 ppm se lit
comme une erreur. **N12 a établi que l'assiette de la mesure est une source
réelle de confusion** ; le suffixe porte précisément cette information.

*À ne pas confondre avec l'exclusion introduite par DT-24 : celle-ci écarte le
hors-**profil**, pas le hors-**fuseau**. Une couche étalée fait toujours grimper
la valeur du candidat dominant, et c'est bien ce que « (tout) » annonce.*
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString, Point

from crs_zone_toolkit.core.analysis import analyze


def _libelles(result) -> dict[int, str]:
    return {d.epsg: d.libelle for d in result.distorsions}


def test_multi_fuseaux_le_candidat_dominant_porte_le_suffixe(
    tp02_lignes_deux_fuseaux, qc_profile, qc_grid
) -> None:
    result = analyze(tp02_lignes_deux_fuseaux, "routes", profile=qc_profile, grid=qc_grid)

    assert len(result.zones_traversees) >= 2, "prémisse : la couche traverse plusieurs fuseaux"
    dominant = result.distorsions[0]
    assert dominant.libelle.endswith(" (tout)")
    assert dominant.libelle.startswith("MTM fuseau ")


def test_mono_fuseau_aucun_suffixe(qc_profile, qc_grid) -> None:
    """Sur une couche d'un seul fuseau, « (tout) » n'oppose rien à rien : c'est du bruit."""
    couche = gpd.GeoDataFrame(geometry=[Point(-73.5 + i * 0.01, 45.5) for i in range(10)], crs=4326)
    result = analyze(couche, "mono", profile=qc_profile, grid=qc_grid)

    assert len(result.zones_traversees) == 1
    assert all("(tout)" not in libelle for libelle in _libelles(result).values())


def test_le_lambert_ne_porte_jamais_le_suffixe(
    tp02_lignes_deux_fuseaux, qc_profile, qc_grid
) -> None:
    """Contre-épreuve : le Lambert couvre toute la province, l'opposition n'a pas de sens."""
    result = analyze(tp02_lignes_deux_fuseaux, "routes", profile=qc_profile, grid=qc_grid)

    lambert = result.distorsions[-1]
    assert "Lambert" in lambert.libelle
    assert "(tout)" not in lambert.libelle


def test_la_recommandation_ne_porte_jamais_le_suffixe(
    tp02_lignes_deux_fuseaux, qc_profile, qc_grid
) -> None:
    """Le suffixe qualifie une MESURE, pas une cible : « reprojeter vers MTM fuseau 8 (tout) »
    n'aurait aucun sens — la maquette ne le montre que dans le tableau."""
    result = analyze(tp02_lignes_deux_fuseaux, "routes", profile=qc_profile, grid=qc_grid)

    assert "(tout)" not in result.recommandation.cible_libelle
    assert "(tout)" not in result.recommandation.motif


def test_le_contrat_json_garde_sa_forme(tp02_lignes_deux_fuseaux, qc_profile, qc_grid) -> None:
    """Changement de **valeur** d'un libellé, jamais de structure."""
    import json

    doc = json.loads(
        analyze(tp02_lignes_deux_fuseaux, "routes", profile=qc_profile, grid=qc_grid).to_json()
    )

    assert doc["schema_version"] == 1
    for entree in doc["distorsion"].values():
        assert set(entree) == {"libelle", "min_ppm", "moy_ppm", "max_ppm"}


def test_le_suffixe_suit_dans_le_rapport_html(qc_profile, qc_grid) -> None:
    """Même information, même endroit : le rapport lit le même libellé."""
    from datetime import UTC, datetime

    from crs_zone_toolkit.core.report import render_html

    couche = gpd.GeoDataFrame(
        geometry=[LineString([(-76.16, y), (-74.16, y)]) for y in (46.0, 46.2, 46.4)], crs=4326
    )
    result = analyze(couche, "routes", profile=qc_profile, grid=qc_grid)
    html = render_html(
        result, couche, profile=qc_profile, grid=qc_grid, generated_at=datetime.now(UTC)
    )

    assert "(tout)" in html
