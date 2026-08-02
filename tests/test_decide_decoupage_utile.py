"""N23 + N20 — le découpage n'est offert, et promis, que s'il découpe (2026-08-02).

**N23** est la plus grave des observations de clôture : le motif
`zone_moins_deformee` affirmait « le découpage par fuseau garde chaque morceau
sous le seuil » alors que, sur les couches concernées, le découpage ne
produirait qu'**un** fichier — inchangé. Bas-Saint-Laurent : 407 ppm, fuseaux
traversés [6, 7, 5], fuseaux **majoritaires** [6].

C'est la racine de **DT-25** — traversés contre produits — mais portée par la
ligne `Motif`, la plus lue de l'écran, et sous forme d'une **affirmation** au
lieu d'un compte. Même classe que **N3** : un énoncé faux avant une décision.

**N20** en est le pendant : l'alternative elle-même était offerte pour un seul
fichier, ce qui équivaut exactement à `--choice zone` sur ce fuseau. Mesuré sur
la SDA : **12 régions multi-fuseaux sur 13**. Le cas dominant, pas un cas limite.

Les deux se corrigent au même endroit, avec la même condition — `_decide`
dispose de `zones_sorties` depuis DT-25.
"""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point

from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.analysis import analyze


def _alt_split(result):
    return next((a for a in result.recommandation.alternatives if a.get("action") == "split"), None)


@pytest.fixture
def une_entite_deux_fuseaux() -> gpd.GeoDataFrame:
    """UNE ligne à cheval sur 75°O : deux fuseaux traversés, un seul majoritaire.

    C'est la forme du cas réel — une région administrative est un polygone, donc
    l'affectation majoritaire la met tout entière dans un fuseau.
    """
    return gpd.GeoDataFrame(geometry=[LineString([(-76.4, 46.0), (-74.4, 46.0)])], crs=4326)


@pytest.fixture
def deux_entites_deux_fuseaux() -> gpd.GeoDataFrame:
    """Deux lignes, chacune majoritaire dans un fuseau différent : le découpage sert."""
    return gpd.GeoDataFrame(
        geometry=[
            LineString([(-77.5, 46.0), (-76.0, 46.0)]),  # majoritaire fuseau 9
            LineString([(-73.5, 46.0), (-72.5, 46.0)]),  # majoritaire fuseau 8
        ],
        crs=4326,
    )


def test_n20_pas_d_alternative_quand_le_decoupage_ne_decoupe_pas(
    une_entite_deux_fuseaux, qc_profile, qc_grid
) -> None:
    result = analyze(une_entite_deux_fuseaux, "x", profile=qc_profile, grid=qc_grid)

    assert len(result.zones_traversees) >= 2, "prémisse : plusieurs fuseaux traversés"
    assert _alt_split(result) is None, "un découpage à une sortie = `--choice zone` déguisé"


def test_n20_l_alternative_reste_quand_le_decoupage_sert(
    deux_entites_deux_fuseaux, qc_profile, qc_grid
) -> None:
    """Contre-épreuve : sans elle, supprimer l'alternative pour de bon passerait."""
    result = analyze(deux_entites_deux_fuseaux, "x", profile=qc_profile, grid=qc_grid)

    alt = _alt_split(result)
    assert alt is not None
    assert len(alt["zones"]) >= 2


def test_n23_le_motif_ne_promet_pas_un_decoupage_impossible(
    une_entite_deux_fuseaux, qc_profile, qc_grid
) -> None:
    """Le cœur de N23 : plus d'affirmation fausse sur la ligne la plus lue."""
    result = analyze(une_entite_deux_fuseaux, "x", profile=qc_profile, grid=qc_grid)
    motif = result.recommandation.motif

    assert "garde chaque morceau" not in motif
    assert "alternative" not in motif.lower()
    if result.recommandation.motif_code in ("zone_moins_deformee", "lambert_moins_deforme"):
        assert "découpage n'aiderait pas" in motif or "découpage n'y changerait rien" in motif


def test_n23_le_motif_promet_le_decoupage_quand_il_tient(
    deux_entites_deux_fuseaux, qc_profile, qc_grid
) -> None:
    """Contre-épreuve : la promesse reste due quand elle est vraie."""
    result = analyze(deux_entites_deux_fuseaux, "x", profile=qc_profile, grid=qc_grid)
    motif = result.recommandation.motif

    assert "découpage" in motif.lower()
    assert "n'aiderait pas" not in motif


def test_n23_les_deux_motifs_concernes_savent_se_taire() -> None:
    """Les constructeurs, en direct : `zone_moins_deformee` ET `lambert_moins_deforme`.

    Le second finissait par « Découpage disponible en alternative. » — aussi faux
    que le premier dès que le découpage ne découpe pas.
    """
    sans = msg.motif_zone_moins_deformee(6, 407, 200, decoupage_utile=False)
    avec = msg.motif_zone_moins_deformee(6, 407, 200, decoupage_utile=True)
    assert "garde chaque morceau" in avec and "garde chaque morceau" not in sans

    sans_l = msg.motif_lambert_moins_deforme(9, 8202, 7456, decoupage_utile=False)
    avec_l = msg.motif_lambert_moins_deforme(9, 8202, 7456, decoupage_utile=True)
    assert "alternative" in avec_l and "alternative" not in sans_l


def test_n20_le_menu_n_offre_pas_un_decoupage_absent(
    une_entite_deux_fuseaux, qc_profile, qc_grid
) -> None:
    """Le menu et le résumé doivent dire la même chose — leçon de la miss de DT-25."""
    result = analyze(une_entite_deux_fuseaux, "x", profile=qc_profile, grid=qc_grid)

    lignes = msg.apply_menu(result)

    assert not [ligne for ligne in lignes if ligne.startswith("  [3]")]
    assert [ligne for ligne in lignes if ligne.startswith("  [0]")], "l'annulation reste offerte"


def test_n20_le_menu_offre_le_decoupage_quand_il_sert(
    deux_entites_deux_fuseaux, qc_profile, qc_grid
) -> None:
    result = analyze(deux_entites_deux_fuseaux, "x", profile=qc_profile, grid=qc_grid)

    lignes = msg.apply_menu(result)

    assert [ligne for ligne in lignes if ligne.startswith("  [3]")]


def test_mono_fuseau_inchange(qc_profile, qc_grid) -> None:
    """Garde : une couche d'un seul fuseau n'a jamais eu d'alternative, et n'en gagne pas."""
    couche = gpd.GeoDataFrame(geometry=[Point(-73.5 + i * 0.01, 45.5) for i in range(5)], crs=4326)
    result = analyze(couche, "mono", profile=qc_profile, grid=qc_grid)

    assert result.recommandation.motif_code == "mono_zone"
    assert result.recommandation.alternatives == ()
