"""Résolution de la cible d'exécution depuis la Decision (SPEC §5.2.1)."""

from crs_zone_toolkit.core.apply import _resolve_target
from crs_zone_toolkit.core.results import Decision
from crs_zone_toolkit.regions.loader import load_profile

QC = load_profile("qc")


class _FauxReco:
    def __init__(self, action, cible):
        self.action, self.cible_epsg = action, cible


class _FauxAnalyse:
    def __init__(self, famille, reco):
        self.famille, self.recommandation = famille, reco


def test_recommendation_reprend_la_reco() -> None:
    a = _FauxAnalyse("wgs84", _FauxReco("zone", 2949))
    assert _resolve_target(a, Decision("recommendation", "auto"), QC) == (2949, "zone")


def test_zone_explicite_selon_famille() -> None:
    a = _FauxAnalyse("nad83", _FauxReco("lambert", 32198))
    assert _resolve_target(a, Decision("zone", "choice", zone=8), QC) == (32188, "zone")


def test_lambert_et_split() -> None:
    a = _FauxAnalyse("csrs", _FauxReco("lambert", 6622))
    assert _resolve_target(a, Decision("lambert", "choice"), QC) == (6622, "lambert")
    assert _resolve_target(a, Decision("split", "choice"), QC) == (None, "split")
