"""Distorsion via get_factors (SPEC §4.2.4, DATA_REFERENCE §6.3, [REF-13])."""

from crs_zone_toolkit.core.analysis import _distortion, _max_abs_ppm


def test_distorsion_au_meridien_central_proche_moins_100_ppm() -> None:
    # MTM fuseau 8 (EPSG:2950), MC = -73,5 : au MC, k0=0,9999 → ~ -100 ppm.
    d = _distortion([-73.5], [46.0], 2950, "MTM fuseau 8")
    assert -130.0 < d.moy_ppm < -80.0


def test_distorsion_croit_vers_le_bord_de_fuseau() -> None:
    bord = _distortion([-77.5], [46.0], 2950, "MTM fuseau 8")  # ~4° du MC
    assert bord.max_ppm > 200.0
    assert _max_abs_ppm(bord) > 200.0


def test_min_moy_max_ordonnes() -> None:
    d = _distortion([-73.5, -75.0, -72.0], [46.0, 46.0, 46.0], 2950, "MTM 8")
    assert d.min_ppm <= d.moy_ppm <= d.max_ppm
