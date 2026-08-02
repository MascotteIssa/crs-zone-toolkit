"""DT-26 — le ⚠ doit signaler ce qui bouge, pas ce qui reste (observations N11, N13).

**N11.** `_datum_warnings` n'émettait un `⚠` que pour `nad27` et `nad83`.
Conséquence : une entrée **NAD83**, dont la famille est *préservée* — le cas le
moins risqué — recevait un `⚠` ; une entrée **WGS 84**, dont la famille *change*
vers CSRS, n'en recevait **aucun**. Le changement était bien **dit** par la ligne
`Datum :`, mais sans la marque visuelle que recevait le cas où rien ne bouge.

Ce n'est pas cosmétique : c'est la **condition de validité du repli CSRS**
(grille d'expertise, question 4). L'écart NAD83(1986) ↔ NAD83(CSRS) est de
l'ordre du mètre au Québec — négligeable en cartographie, pas en cadastral. Un
repli d'un mètre sur une source non identifiée doit être marqué.

**Le marqueur va sur la ligne `Datum :` elle-même.** L'ancien avertissement
NAD83 *répétait* cette ligne (« entrée NAD83 d'origine → famille préservée »
contre « Entrée en NAD83 d'origine : la famille est préservée ») : porter la
marque là où le fait est énoncé supprime la redite et corrige la hiérarchie d'un
seul geste.

**N13.** Sur un `.prj` sans code EPSG, l'écran affichait `CRS déclaré unknown
(géographique)` puis `Datum : entrée WGS 84 → …`. Les deux sont exacts et
parlent de **niveaux différents** — le *code* du CRS est irrésoluble, son
*datum* est lisible — mais rien ne le disait : un lecteur peut y voir une
contradiction. (Vérifié sur la couche RTSS : `to_epsg() is None`, `name` vaut
littéralement `"unknown"`, et le datum est bien reconnu comme WGS 84.)
"""

from __future__ import annotations

import pytest

from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.analysis import _datum_warnings
from crs_zone_toolkit.core.targets import target_family

# Familles dont la recommandation PRÉSERVE le datum d'entrée.
PRESERVEES = ["nad83", "csrs"]
# Familles dont la recommandation CHANGE la famille (repli CSRS).
CHANGEES = ["wgs84", "nad27", "famille_inconnue"]


@pytest.mark.parametrize("famille", PRESERVEES)
def test_dt26_une_famille_preservee_n_emet_aucun_avertissement(famille: str) -> None:
    """Le cas le moins risqué ne doit plus produire de `⚠` (N11)."""
    assert famille == target_family(famille), "prémisse : cette famille est bien préservée"
    assert _datum_warnings(famille) == []


def test_dt26_nad27_avertit_toujours_de_la_grille_ntv2() -> None:
    """Contre-épreuve : NAD27 reste le cas à risque — une grille NTv2 est requise.

    Sans elle, « ne plus rien avertir » passerait le test ci-dessus.
    """
    assert _datum_warnings("nad27") == [msg.NAD27_NTV2]


@pytest.mark.parametrize("famille", PRESERVEES)
def test_dt26_la_preservation_recoit_une_marque_positive(famille: str) -> None:
    assert msg.marque_datum(famille, target_family(famille)) == msg.MARQUE_DATUM_PRESERVE


@pytest.mark.parametrize("famille", CHANGEES)
def test_dt26_le_changement_de_famille_recoit_le_signe_d_alerte(famille: str) -> None:
    """Le cœur de l'inversion : c'est le repli, pas la préservation, qui s'annonce."""
    assert msg.marque_datum(famille, target_family(famille)) == msg.MARQUE_DATUM_CHANGE


def test_dt26_la_note_csrs_reste_disponible_mais_n_est_plus_un_avertissement() -> None:
    """« NAD83(CSRS) est le standard actuel » est un conseil, pas une alerte.

    La chaîne est **conservée** : elle transite par le rapport HTML validé le
    17/07 (divergence DT-20 (3), arbitrée « maquette amendée »). Seul son statut
    change — note neutre au lieu d'avertissement.
    """
    assert msg.analyse_note_datum("nad83") == msg.CSRS_STANDARD_ACTUEL
    assert msg.CSRS_STANDARD_ACTUEL not in _datum_warnings("nad83")
    for famille in ("csrs", "wgs84", "nad27", "famille_inconnue"):
        assert msg.analyse_note_datum(famille) is None


# ── N13 — « code du CRS » contre « datum » ─────────────────────────────────


def test_dt26_sans_code_epsg_la_ligne_dit_que_le_datum_est_ailleurs() -> None:
    """Cas RTSS : `to_epsg()` est None, le nom vaut « unknown », le datum est lisible."""
    ligne = msg.analyse_ligne_crs_declare(None, "unknown", geographique=True)

    assert "unknown" in ligne
    assert "(géographique)" in ligne
    assert "datum" in ligne.lower(), "rien ne renvoyait le lecteur à la ligne Datum"
    assert len(ligne) <= 99, "une ligne qui déborde s'enveloppe en colonne 0 (N18)"


def test_dt26_avec_un_code_epsg_la_ligne_est_inchangee() -> None:
    """Contre-épreuve : la mention ne concerne que le CRS sans code résolu."""
    ligne = msg.analyse_ligne_crs_declare(4326, "WGS 84", geographique=True)

    assert ligne == "CRS déclaré EPSG:4326 — WGS 84 (géographique)"
