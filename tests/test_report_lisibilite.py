"""DT-28 — la section « Distorsion mesurée » du rapport doit se lire (N15, N9).

**N15.** Le rapport n'expliquait **jamais** le sens du signe. Comptage sur un
rapport réel lors du test manuel : `compression`, `dilatation`, `contraction`,
`plus court`, `plus long` y apparaissaient **zéro fois** ; seul « ppm »
figurait. L'échelle est pourtant **divergente, centrée sur 0** — sa lecture
repose entièrement sur ce sens. Preuve faite sur le terrain : un géomaticien a
répondu « je n'ai pas compris » à la case « le signe est-il évident ? ».

**N9.** Le paragraphe de méthodologie compactait quatre notions en trois
phrases, pour un lecteur qui a une base en géomatique mais n'est pas
spécialiste des projections.

Même section, même lecteur, même remède : une seule réécriture.

Assertions portées sur le **fichier produit**, ce que TEST_PLAN §5 autorise
explicitement — contrairement au texte terminal.
"""

from __future__ import annotations

from datetime import UTC, datetime

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from crs_zone_toolkit.core.analysis import analyze
from crs_zone_toolkit.core.report import render_html

_QUAND = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def rapport(qc_profile, qc_grid) -> str:
    couche = gpd.GeoDataFrame(
        geometry=[LineString([(-76.16, y), (-74.16, y)]) for y in (46.0, 46.2, 46.4)],
        crs=4326,
    )
    result = analyze(couche, "routes", profile=qc_profile, grid=qc_grid)
    return render_html(result, couche, profile=qc_profile, grid=qc_grid, generated_at=_QUAND)


def test_n15_le_rapport_dit_ce_que_signifie_un_ppm_negatif(rapport: str) -> None:
    """Négatif = distances projetées plus COURTES que sur le terrain."""
    assert "plus courtes" in rapport
    assert "compression" in rapport


def test_n15_le_rapport_dit_ce_que_signifie_un_ppm_positif(rapport: str) -> None:
    """Les deux sens doivent être nommés : donner un seul laisse deviner l'autre."""
    assert "plus longues" in rapport
    assert "dilatation" in rapport


def test_n15_le_sens_du_signe_precede_l_echelle_divergente(rapport: str) -> None:
    """L'explication ne sert à rien après le graphique qu'elle conditionne."""
    position_signe = rapport.find("plus courtes")
    position_echelle = rapport.find('class="scale"')

    assert position_signe != -1 and position_echelle != -1
    assert position_signe < position_echelle


def test_n9_la_methodologie_dit_ce_qu_est_un_facteur_d_echelle(rapport: str) -> None:
    """Autosuffisance : le lecteur n'a pas à savoir d'avance ce qu'on mesure."""
    assert "facteur d'échelle" in rapport.lower()
    assert "ppm" in rapport
    assert "parties par million" in rapport.lower()


def test_n9_la_methodologie_donne_un_ordre_de_grandeur_concret(rapport: str) -> None:
    """« 100 ppm = 10 cm par kilomètre » : la seule phrase qui rendait le chiffre palpable."""
    assert "10 cm" in rapport
    assert "kilomètre" in rapport.lower() or "km" in rapport


def test_n9_la_methodologie_justifie_le_zero_comme_centre(rapport: str) -> None:
    """Pourquoi l'échelle est centrée sur 0, et pas seulement qu'elle l'est."""
    assert "centrée sur 0" in rapport


def test_dt28_le_rapport_reste_auto_porte(rapport: str) -> None:
    """Garde SPEC §7 : la réécriture n'introduit aucune ressource externe."""
    assert "http://" not in rapport
    assert "https://" not in rapport
