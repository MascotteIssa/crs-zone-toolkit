"""Résolution des cibles EPSG selon la famille (core/targets.py — partagé analysis/apply).

Inclut les tests DT-18 : refus explicite (UnknownRegionError) quand la famille
cible n'a pas de code, au lieu du repli CSRS silencieux.
"""

import pytest

from crs_zone_toolkit.core.errors import UnknownRegionError
from crs_zone_toolkit.core.profile import Fuseau, RegionProfile, Seuils
from crs_zone_toolkit.core.targets import (
    fuseau_par_zone,
    lambert_epsg,
    target_family,
    zone_epsg,
)
from crs_zone_toolkit.regions.loader import load_profile

QC = load_profile("qc")


def test_target_family() -> None:
    assert target_family("csrs") == "csrs"
    assert target_family("nad83") == "nad83"
    assert target_family("nad27") == "csrs"
    assert target_family("wgs84") == "csrs"


def test_zone_et_lambert_epsg() -> None:
    assert zone_epsg(fuseau_par_zone(QC, 8), "csrs") == 2950
    assert zone_epsg(fuseau_par_zone(QC, 8), "nad83") == 32188
    assert lambert_epsg(QC, "csrs") == 6622
    assert lambert_epsg(QC, "nad83") == 32198


def _fuseau_sans_nad83() -> Fuseau:
    # Codes factices arbitraires : zone_epsg est un pur lookup, pyproj n'est pas sollicité.
    return Fuseau(
        zone=7,
        meridien_central=-70.5,
        lon_min=-72.0,
        lon_max=-69.0,
        epsg_csrs=1111,
        epsg_nad83=None,
        epsg_nad27=None,
    )


def _profil_sans_nad83() -> RegionProfile:
    return RegionProfile(
        id="fx",
        nom="Factice",
        version="test",
        grille="g.geojson",
        limite="l.geojson",
        seuils=Seuils(part_dominante_min=0.9, distorsion_max_ppm=200, n_echantillons=50),
        famille_defaut="csrs",
        familles_grille_obligatoire=(),
        geographiques={"csrs": 1000},
        multi_zones={"csrs": 2222},
        fuseaux=(_fuseau_sans_nad83(),),
    )


def test_zone_epsg_famille_sans_code_leve_au_lieu_du_repli_csrs() -> None:
    """DT-18 : famille cible sans code au fuseau → erreur explicite, jamais le code CSRS."""
    with pytest.raises(UnknownRegionError, match="nad83"):
        zone_epsg(_fuseau_sans_nad83(), "nad83")


def test_zone_epsg_famille_presente_inchangee() -> None:
    assert zone_epsg(_fuseau_sans_nad83(), "csrs") == 1111


def test_lambert_epsg_famille_sans_code_leve_au_lieu_du_repli_csrs() -> None:
    with pytest.raises(UnknownRegionError, match="nad83"):
        lambert_epsg(_profil_sans_nad83(), "nad83")


def test_lambert_epsg_famille_presente_inchangee() -> None:
    assert lambert_epsg(_profil_sans_nad83(), "csrs") == 2222
