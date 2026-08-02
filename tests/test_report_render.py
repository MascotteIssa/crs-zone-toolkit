"""render_html : rapport auto-porté, fidèle à AnalysisResult (SPEC §7)."""

import re
from dataclasses import replace
from datetime import UTC, datetime

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from crs_zone_toolkit.core import analysis
from crs_zone_toolkit.core.report import render_html
from crs_zone_toolkit.core.results import Distorsion

_QUAND = datetime(2026, 7, 14, 14, 32, tzinfo=UTC)


def _analyse(layer, nom, qc_profile, qc_grid):
    return analysis.analyze(layer, nom, profile=qc_profile, grid=qc_grid)


@pytest.fixture
def html_multizone(qc_profile, qc_grid):
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    res = _analyse(layer, "routes", qc_profile, qc_grid)
    return render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )


def test_html_auto_porte(html_multizone) -> None:
    """Un seul fichier : carte embarquée, aucune ressource http externe."""
    assert "data:image/png;base64," in html_multizone
    assert "http://" not in html_multizone
    assert "https://" not in html_multizone


def test_html_contient_recommandation_et_couche(html_multizone) -> None:
    assert "routes" in html_multizone
    assert "Recommandation" in html_multizone
    # multi-fuseaux sans domination → Québec Lambert
    assert "Lambert" in html_multizone


def test_html_liste_les_fuseaux_traverses(html_multizone) -> None:
    assert "Fuseau 9" in html_multizone
    assert "Fuseau 8" in html_multizone


def test_html_mention_nad83_origine(qc_profile, qc_grid) -> None:
    lignes = [LineString([(-76.16, 46.0), (-74.16, 46.0)])]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4269)  # NAD83 d'origine
    res = _analyse(layer, "c", qc_profile, qc_grid)
    html = render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    assert "NAD83 d'origine" in html


def test_html_cas_hors_profil_ne_lit_pas_cible(qc_profile, qc_grid) -> None:
    """action == 'aucune' : rendu sans bloc cible, pas de KeyError/plantage."""
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy([-97.15, -97.14], [49.9, 49.91]), crs=4326)
    res = _analyse(pts, "winnipeg", qc_profile, qc_grid)
    assert res.recommandation.action == "aucune"
    html = render_html(
        layer=pts, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    assert "hors" in html.lower()  # message hors-profil présent
    assert "EPSG:0" not in html  # la sentinelle 0 n'est jamais affichée comme cible


def test_html_echappe_le_contenu_hostile(qc_profile, qc_grid) -> None:
    """Injection HTML : le contenu variable (nom de couche) est échappé, pas exécuté."""
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    res = _analyse(layer, "routes", qc_profile, qc_grid)
    res = replace(res, couche="<script>alert(1)</script>")
    html = render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    assert "<script>alert(1)</script>" not in html  # jamais de balise brute injectée
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html  # rendue échappée


def test_html_echappe_les_avertissements(qc_profile, qc_grid) -> None:
    """Invariant : les avertissements sont échappés (jamais rendus comme HTML de confiance)."""
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    res = _analyse(layer, "routes", qc_profile, qc_grid)
    res = replace(res, avertissements=("<img src=x onerror=alert(1)>",))
    html = render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    # marqueur propre à l'injection (`src=x`, sans guillemet) : ne heurte pas la
    # balise <img src="data:..."> légitime de la carte.
    assert "<img src=x onerror" not in html  # jamais de balise brute injectée
    assert "&lt;img src=x onerror" in html  # rendu échappé


def test_rapport_utilise_le_moins_unicode(qc_profile, qc_grid, tp02_lignes_deux_fuseaux) -> None:
    """Cellules de distorsion : le signe moins Unicode − (U+2212), pas le tiret ASCII."""
    layer = tp02_lignes_deux_fuseaux
    res = _analyse(layer, "couche", qc_profile, qc_grid)
    html = render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    assert "−" in html  # au moins une distorsion négative → signe moins Unicode


def test_html_famille_autre_couverte(qc_profile, qc_grid) -> None:
    """Une famille de datum non reconnue ('autre') rend une note non vide, sans plantage."""
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    res = _analyse(layer, "routes", qc_profile, qc_grid)
    res = replace(res, famille="autre")
    html = render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    assert "Autre datum" in html  # libellé de famille non vide
    # la note datum est rendue avec son texte réel (jamais vide) — assertion
    # indépendante du balisage (l'ancienne visait une chaîne CSS du template).
    assert "n'est pas reconnue par le profil" in html


# ── Rendu premium : thème clair/sombre commutable + échelle divergente ──────


def test_html_offre_une_bascule_de_theme(html_multizone) -> None:
    """Un seul fichier propose clair/sombre : bouton, suivi de l'OS, choix mémorisé."""
    assert 'aria-label="Basculer' in html_multizone  # bouton accessible
    assert "data-theme" in html_multizone  # attribut de thème piloté
    assert "prefers-color-scheme" in html_multizone  # défaut = réglage de l'OS
    assert "crszone-theme" in html_multizone  # choix mémorisé (localStorage)


def test_html_definit_une_palette_sombre(html_multizone) -> None:
    """La palette sombre est dans le même fichier (auto-porté), pilotée par data-theme."""
    assert '[data-theme="dark"]' in html_multizone


def test_html_reste_auto_porte_avec_le_theme(html_multizone) -> None:
    """Le JS du thème n'introduit aucune ressource externe (invariant SPEC §7)."""
    assert "http://" not in html_multizone
    assert "https://" not in html_multizone


def test_impression_masque_le_bouton_de_theme(html_multizone) -> None:
    """À l'impression le bouton disparaît (le sombre imprime mal → forcé clair)."""
    assert re.search(r"@media print[\s\S]*theme-toggle", html_multizone)


def test_html_regle_de_decision_lisible(html_multizone) -> None:
    """La règle de décision est en clair pour l'utilisateur, pas une référence de doc interne."""
    assert "SPEC §4.3" not in html_multizone  # plus de jargon de spec dans le rapport
    assert "la moins déformée" in html_multizone  # règle B2 « distorsion d'abord » en clair
    assert "part_dominante_min" not in html_multizone  # seuil vestigial retiré du rapport


def test_html_rend_l_echelle_divergente(html_multizone) -> None:
    """La distorsion est rendue en échelle centrée sur 0 (bande de tolérance + zéro)."""
    assert 'class="scale"' in html_multizone
    assert 'class="tol"' in html_multizone
    assert 'class="zero"' in html_multizone


def test_html_facteur_signale_l_ampleur_du_depassement(qc_profile, qc_grid) -> None:
    """Un candidat très hors seuil affiche de combien il franchit la tolérance (≈ ×N)."""
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    res = _analyse(layer, "routes", qc_profile, qc_grid)
    grosse = Distorsion(
        libelle="MTM fuseau 8", epsg=32188, min_ppm=-100.0, moy_ppm=1654.0, max_ppm=14784.0
    )
    res = replace(res, distorsions=(grosse,))  # seuil par défaut = 200 ppm
    html = render_html(
        layer=layer, analysis=res, profile=qc_profile, grid=qc_grid, generated_at=_QUAND
    )
    assert "×74" in html  # 14784 / 200 ≈ 74
    assert "tolérance" in html
