"""Tests dorés des écrans de CLI_UX.md — exception autorisée par TEST_PLAN §7.

Seuls tests de la suite autorisés à asserter du texte terminal. Ils verrouillent
la fidélité à la maquette (DT-02 puis DT-14 sont nés de son absence).
"""

from __future__ import annotations

import io
from pathlib import Path

import geopandas as gpd
from rich.console import Console
from shapely.geometry import Point

import crs_zone_toolkit
from crs_zone_toolkit import affichage
from crs_zone_toolkit.core.analysis import analyze
from crs_zone_toolkit.core.targets import target_family


def _rendu(
    result,
    profile,
    *,
    couche: str,
    n_entites: int,
    geographique: bool,
    abrege: bool = False,
    avec_rapport: bool = True,
) -> list[str]:
    """Rend le résumé dans une console à largeur fixe, sans couleur, et renvoie ses lignes."""
    tampon = io.StringIO()
    console = Console(file=tampon, width=80, no_color=True, legacy_windows=False)
    chemin_rapport = Path(f"{couche}_analyse_crs.html") if avec_rapport else None
    affichage.resume_analyse(
        console,
        result,
        chemin_rapport,
        couche=Path(f"{couche}.gpkg"),
        n_entites=n_entites,
        profile=profile,
        crs_geographique=geographique,
        famille_cible=target_family(result.famille),
        abrege=abrege,
    )
    return [ligne.rstrip() for ligne in tampon.getvalue().splitlines()]


def test_maquette_cli_ux_section2_mono_fuseau(qc_profile, qc_grid) -> None:
    """CLI_UX §2 : en-tête + version, filet, CRS géographique, fuseau avec MC et barre."""
    pts = [Point(-71.9 + i * 0.01, 45.4) for i in range(20)]  # fuseau 7
    layer = gpd.GeoDataFrame(geometry=pts, crs=4326)
    result = analyze(layer, "hydro", profile=qc_profile, grid=qc_grid)
    lignes = _rendu(result, qc_profile, couche="hydro", n_entites=len(pts), geographique=True)

    version = crs_zone_toolkit.__version__
    assert lignes[0].startswith("Analyse CRS : profil Québec (qc)")
    assert lignes[0].rstrip().endswith(f"crszone {version}")
    assert set(lignes[1]) == {"─"} and len(lignes[1]) == 80  # filet pleine largeur
    assert lignes[2].startswith("Couche      hydro.gpkg (20 entités, points)")
    assert lignes[3] == "CRS déclaré EPSG:4326, WGS 84 (géographique)"
    assert lignes[4].startswith("Emprise     ")

    titre = next(
        i for i, ligne in enumerate(lignes) if ligne.startswith("Répartition par fuseau MTM")
    )
    assert lignes[titre] == "Répartition par fuseau MTM (part de l'effectif total)"
    ligne_fuseau = lignes[titre + 1]
    assert ligne_fuseau.startswith("  Fuseau 7 (MC −70,5°)  ")  # U+2212, virgule française
    assert "█" * 20 in ligne_fuseau  # 100 % → barre pleine (échelle 20 caractères)
    assert ligne_fuseau.rstrip().endswith("100,0 %")


def test_maquette_cli_ux_section3_multi_fuseaux(
    qc_profile, qc_grid, tp02bis_deux_fuseaux_majoritaires
) -> None:
    """CLI_UX §3 : répartition par part de longueur, tableau de distorsion avec en-tête,
    alternative découpage, recommandation préfixée avec famille.

    Couche changée le 2026-08-02 (N20/N23) : la maquette **montre** la ligne
    « Alternative : découpage ». Elle exige donc une couche à **deux fuseaux
    majoritaires** — `tp02_lignes_deux_fuseaux` n'en a qu'un, ses trois lignes étant
    toutes à cheval, et n'a donc plus d'alternative à afficher. La nouvelle fixture
    reproduit les parts exactes de la maquette (58,3 % / 41,7 %).
    """
    couche = tp02bis_deux_fuseaux_majoritaires
    result = analyze(couche, "routes", profile=qc_profile, grid=qc_grid)
    lignes = _rendu(
        result,
        qc_profile,
        couche="routes",
        n_entites=len(couche),
        geographique=True,
    )

    titre = next(
        i for i, ligne in enumerate(lignes) if ligne.startswith("Répartition par fuseau MTM")
    )
    assert lignes[titre] == "Répartition par fuseau MTM (part de la longueur totale)"

    # Deux lignes de fuseau, ordonnées par part décroissante (fuseau 9 : 58 % > fuseau 8 : 42 %).
    ligne_zone_1 = lignes[titre + 1]
    ligne_zone_2 = lignes[titre + 2]
    assert "Fuseau 9" in ligne_zone_1
    assert "Fuseau 8" in ligne_zone_2

    entete_distorsion = next(
        i for i, ligne in enumerate(lignes) if ligne.startswith("Distorsion mesurée")
    )
    ligne_entete_colonnes = lignes[entete_distorsion + 1]
    assert ligne_entete_colonnes.startswith("  Candidat")
    assert ligne_entete_colonnes.rstrip().endswith("max")

    assert any("Alternative : découpage par fuseau" in ligne for ligne in lignes)

    ligne_reco = next(i for i, ligne in enumerate(lignes) if "Recommandation :" in ligne)
    assert "reprojeter vers" in lignes[ligne_reco]
    assert "(EPSG:" in lignes[ligne_reco] and lignes[ligne_reco].rstrip().endswith(")")


def test_maquette_cli_ux_section5_apply_auto_resume_abrege(qc_profile, qc_grid) -> None:
    """CLI_UX §5 : `apply --auto`/`--choice` affiche le résumé en mode abrégé (DT-20 n°5) —
    en-tête, Couche, CRS déclaré, Emprise, Recommandation et Motif, sans répartition par
    fuseau ni tableau de distorsion (DT-20 n°6, contenu non retouché par cette tâche).

    `apply` n'écrit aucun rapport HTML : `chemin_rapport=None` doit omettre la ligne
    « Rapport détaillé » sans faire disparaître la ligne « Pour appliquer » qui la suit.
    """
    pts = [Point(-71.9 + i * 0.01, 45.4) for i in range(20)]  # fuseau 7
    layer = gpd.GeoDataFrame(geometry=pts, crs=4326)
    result = analyze(layer, "hydro", profile=qc_profile, grid=qc_grid)
    lignes = _rendu(
        result,
        qc_profile,
        couche="hydro",
        n_entites=len(pts),
        geographique=True,
        abrege=True,
        avec_rapport=False,
    )

    version = crs_zone_toolkit.__version__
    assert lignes[0].startswith("Analyse CRS : profil Québec (qc)")
    assert lignes[0].rstrip().endswith(f"crszone {version}")
    assert set(lignes[1]) == {"─"} and len(lignes[1]) == 80  # filet pleine largeur
    assert lignes[2].startswith("Couche      hydro.gpkg (20 entités, points)")
    assert lignes[3] == "CRS déclaré EPSG:4326, WGS 84 (géographique)"
    assert lignes[4].startswith("Emprise     ")

    assert not any(ligne.startswith("Répartition par fuseau MTM") for ligne in lignes)
    assert not any(ligne.startswith("Distorsion mesurée") for ligne in lignes)

    ligne_reco = next(i for i, ligne in enumerate(lignes) if "Recommandation :" in ligne)
    assert lignes[ligne_reco + 1].strip().startswith("Motif :")

    assert not any("Rapport détaillé" in ligne for ligne in lignes)  # aucun rapport côté apply
    assert any(ligne.strip().startswith("Pour appliquer") for ligne in lignes)


def test_maquette_cli_ux_section4_apply_interactif_resume_complet_sans_rapport(
    qc_profile, qc_grid, tp02_lignes_deux_fuseaux
) -> None:
    """CLI_UX §4 : `apply` interactif (défaut, sans `--auto`/`--choice`) « reprend l'affichage
    de l'analyse (§3) » — résumé **complet** (`abrege=False`), donc répartition par fuseaux,
    tableau de distorsion et recommandation, avant le menu de décision (revue relecteur frais,
    constat Important 2 : ce régime — `abrege=False` + `chemin_rapport=None` — n'était verrouillé
    par aucun doré ; c'est pourtant le chemin le plus courant, l'interactif étant le défaut).

    `apply` n'écrit aucun rapport HTML : `chemin_rapport=None` doit omettre la ligne « Rapport
    détaillé » sans faire disparaître le reste du résumé complet.
    """
    result = analyze(tp02_lignes_deux_fuseaux, "routes", profile=qc_profile, grid=qc_grid)
    lignes = _rendu(
        result,
        qc_profile,
        couche="routes",
        n_entites=len(tp02_lignes_deux_fuseaux),
        geographique=True,
        abrege=False,
        avec_rapport=False,
    )

    # Résumé complet : répartition par fuseau ET tableau de distorsion présents (contrairement
    # au mode abrégé §5), même sans rapport.
    assert any(ligne.startswith("Répartition par fuseau MTM") for ligne in lignes)
    assert any(ligne.startswith("Distorsion mesurée") for ligne in lignes)
    assert any("Recommandation :" in ligne for ligne in lignes)

    # Seule la ligne « Rapport détaillé » disparaît — le reste de l'écran §3 est intact.
    assert not any("Rapport détaillé" in ligne for ligne in lignes)
    assert any(ligne.strip().startswith("Pour appliquer") for ligne in lignes)
