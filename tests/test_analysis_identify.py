"""Identification CRS/famille/reconnaissance (SPEC §4.2.1, DATA_REFERENCE §1/§4.2)."""

import pytest
from pyproj import CRS

from crs_zone_toolkit.core.analysis import _identify
from crs_zone_toolkit.regions.loader import load_profile


@pytest.fixture(scope="module")
def qc():
    return load_profile("qc")


@pytest.mark.parametrize(
    "code, famille",
    [
        (4326, "wgs84"),  # géographique WGS84
        (4617, "csrs"),  # géographique CSRS
        (4269, "nad83"),  # géographique NAD83 origine
        (2949, "csrs"),  # MTM 7 CSRS
        (32188, "nad83"),  # MTM 8 NAD83
        (32084, "nad27"),  # MTM 4 NAD27
        (6622, "csrs"),  # Québec Lambert CSRS
        (32198, "nad83"),  # Québec Lambert NAD83
    ],
)
def test_famille_par_lookup_profil(qc, code: int, famille: str) -> None:
    _epsg, _etq, fam, _rec = _identify(CRS.from_epsg(code), qc)
    assert fam == famille


@pytest.mark.parametrize(
    "code, famille",
    [
        (2944, "csrs"),  # SCoPQ zone 2 — hors index profil → repli datum pyproj
        (3798, "nad83"),  # MTQ Lambert NAD83 — repli datum
    ],
)
def test_famille_par_repli_pyproj(qc, code: int, famille: str) -> None:
    _epsg, _etq, fam, _rec = _identify(CRS.from_epsg(code), qc)
    assert fam == famille


@pytest.mark.parametrize(
    "code, etiquette",
    [
        (2944, "SCoPQ zone 2"),
        (3798, "MTQ Lambert"),
        (6623, "Québec Albers"),
    ],
)
def test_crs_reconnu(qc, code: int, etiquette: str) -> None:
    _epsg, _etq, _fam, rec = _identify(CRS.from_epsg(code), qc)
    assert rec == etiquette


def test_crs_non_reconnu_donne_none(qc) -> None:
    _epsg, _etq, _fam, rec = _identify(CRS.from_epsg(4326), qc)
    assert rec is None
