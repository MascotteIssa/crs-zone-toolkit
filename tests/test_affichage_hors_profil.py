"""DT-22 — l'écran « 100 % hors profil », par le câblage et non par le texte.

`CLI_UX.md` ne décrit **pas** cet écran (son §6.4 ne couvre que le cas
*partiellement* hors profil) : un test doré dépasserait l'exception bornée de
TEST_PLAN §7. Ces tests assertent donc **quelles chaînes sont demandées**, pas
ce qu'elles contiennent — conforme à TEST_PLAN §5, et c'est le motif de la
séparation en deux étages :

- `tests/test_messages.py` garde le **contenu** (aucune famille ne rend
  `EPSG:0`), balayé sur les cinq familles ;
- ce fichier garde le **câblage** (`action` est bien transmis, la section vide
  reçoit sa ligne, `Pour appliquer` disparaît).

Sans cet étage, les correctifs d'`affichage.py` ne mordaient sur rien : la
suite est passée verte **avant comme après** — le piège même de la Phase C.

La couche de reproduction est celle du terrain : une couche **ontarienne en
NAD83 (4269)**, sans `--assume-crs` ni erreur d'usage. C'est la famille dont la
ligne « Datum » fuyait, sur le cas « mauvaise région » le plus banal qui soit
pour un outil québécois.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import geopandas as gpd
import pytest
from rich.console import Console
from shapely.geometry import Point

from crs_zone_toolkit import affichage
from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.analysis import analyze
from crs_zone_toolkit.core.targets import target_family


@pytest.fixture
def toronto_nad83() -> gpd.GeoDataFrame:
    """6 points à Toronto, déclarés en EPSG:4269 (NAD83 d'origine).

    Hors de la limite du Québec, donc hors profil à 100 % — mais dans la bande
    de longitude du fuseau 10 : la couche n'est pas absurde, elle est ailleurs.
    """
    pts = [Point(-79.42 + i * 0.01, 43.66 + i * 0.01) for i in range(6)]
    return gpd.GeoDataFrame(geometry=pts, crs=4269)


@pytest.fixture
def montreal_nad83() -> gpd.GeoDataFrame:
    """Contre-épreuve : la même couche, mais en plein fuseau 8 (MC −73,5°)."""
    pts = [Point(-73.55 + i * 0.01, 45.50 + i * 0.01) for i in range(6)]
    return gpd.GeoDataFrame(geometry=pts, crs=4269)


def _rendre(layer: gpd.GeoDataFrame, profile: Any, grid: Any) -> Any:
    result = analyze(layer, "couche", profile=profile, grid=grid)
    console = Console(file=io.StringIO(), width=80, no_color=True, legacy_windows=False)
    affichage.resume_analyse(
        console,
        result,
        None,
        couche=Path("couche.gpkg"),
        n_entites=len(layer),
        profile=profile,
        crs_geographique=True,
        famille_cible=target_family(result.famille),
    )
    return result


def test_la_couche_de_reference_est_bien_100_pourcent_hors_profil(
    toronto_nad83, qc_profile, qc_grid
) -> None:
    """Garde-fou : si la limite du profil changeait, les tests suivants passeraient à vide."""
    result = analyze(toronto_nad83, "couche", profile=qc_profile, grid=qc_grid)

    assert result.recommandation.action == "aucune"
    assert not result.zones_traversees
    assert result.famille == "nad83", "c'est la famille dont la ligne Datum fuyait"
    assert result.recommandation.cible_epsg == 0, "la sentinelle SPEC §8"


def test_action_aucune_est_transmise_a_la_ligne_datum(
    toronto_nad83, qc_profile, qc_grid, monkeypatch
) -> None:
    """Le câblage du correctif `EPSG:0` : sans `action`, la ligne ne peut pas se garder."""
    recu: dict[str, Any] = {}
    vrai = msg.analyse_ligne_datum

    def espion(famille: str, cible_epsg: int, *, action: str) -> str:
        recu.update(famille=famille, cible_epsg=cible_epsg, action=action)
        return vrai(famille, cible_epsg, action=action)

    monkeypatch.setattr(msg, "analyse_ligne_datum", espion)
    _rendre(toronto_nad83, qc_profile, qc_grid)

    assert recu["action"] == "aucune"
    assert recu["famille"] == "nad83"


def test_section_repartition_vide_recoit_sa_ligne(
    toronto_nad83, qc_profile, qc_grid, monkeypatch
) -> None:
    """N6 : un titre annoncé sans ligne se lit comme un bug de rendu."""
    appels: list[str] = []
    monkeypatch.setattr(msg, "analyse_repartition_vide", lambda: appels.append("vide") or "…")
    monkeypatch.setattr(msg, "analyse_bloc_fuseaux", lambda _: appels.append("bloc") or [])

    _rendre(toronto_nad83, qc_profile, qc_grid)

    assert appels == ["vide"], "la ligne d'explication remplace le bloc, elle ne s'y ajoute pas"


def test_section_repartition_garnie_n_appelle_pas_la_ligne_vide(
    montreal_nad83, qc_profile, qc_grid, monkeypatch
) -> None:
    """Contre-épreuve : sur une couche en profil, rien ne change."""
    appels: list[str] = []
    monkeypatch.setattr(msg, "analyse_repartition_vide", lambda: appels.append("vide") or "…")
    monkeypatch.setattr(
        msg, "analyse_bloc_fuseaux", lambda lignes: appels.append("bloc") or ["  Fuseau 8"]
    )

    _rendre(montreal_nad83, qc_profile, qc_grid)

    assert appels == ["bloc"]


def test_pour_appliquer_disparait_quand_rien_n_est_recommande(
    toronto_nad83, qc_profile, qc_grid, monkeypatch
) -> None:
    """N6 : proposer d'appliquer alors qu'il n'y a rien à appliquer."""
    appels: list[str] = []
    monkeypatch.setattr(msg, "analyse_pour_appliquer", lambda nom: appels.append(nom) or "…")

    _rendre(toronto_nad83, qc_profile, qc_grid)

    assert appels == []


def test_pour_appliquer_reste_quand_une_cible_existe(
    montreal_nad83, qc_profile, qc_grid, monkeypatch
) -> None:
    """Contre-épreuve : sans elle, supprimer la ligne pour de bon passerait le test ci-dessus."""
    appels: list[str] = []
    monkeypatch.setattr(msg, "analyse_pour_appliquer", lambda nom: appels.append(nom) or "…")

    _rendre(montreal_nad83, qc_profile, qc_grid)

    assert appels == ["couche.gpkg"]
