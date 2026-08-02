"""Sélection des codes cibles selon la famille (DATA_REFERENCE §1)."""

from crs_zone_toolkit.core.targets import (
    fuseau_par_zone as _fuseau_par_zone,
)
from crs_zone_toolkit.core.targets import (
    lambert_epsg as _lambert_epsg,
)
from crs_zone_toolkit.core.targets import (
    target_family as _target_family,
)
from crs_zone_toolkit.core.targets import (
    zone_epsg as _zone_epsg,
)
from crs_zone_toolkit.regions.loader import load_profile

QC = load_profile("qc")


def test_target_family() -> None:
    assert _target_family("csrs") == "csrs"
    assert _target_family("nad83") == "nad83"
    assert _target_family("nad27") == "csrs"  # NAD27 jamais reconduit (règle §1.5)
    assert _target_family("wgs84") == "csrs"
    assert _target_family("autre") == "csrs"


def test_zone_epsg_selon_famille() -> None:
    f8 = _fuseau_par_zone(QC, 8)
    assert _zone_epsg(f8, "csrs") == 2950
    assert _zone_epsg(f8, "nad83") == 32188


def test_lambert_epsg_selon_famille() -> None:
    assert _lambert_epsg(QC, "csrs") == 6622
    assert _lambert_epsg(QC, "nad83") == 32198
