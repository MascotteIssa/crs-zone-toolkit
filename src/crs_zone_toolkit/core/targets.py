"""Résolution des cibles EPSG à partir du profil et de la famille de datum.

Concern partagé par le noyau analysis (recommandation) et apply (exécution).
Aucune valeur géodésique en dur (TP-40) : tout vient du RegionProfile injecté.
"""

from __future__ import annotations

from pyproj import CRS

from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.errors import UnknownRegionError
from crs_zone_toolkit.core.profile import Fuseau, RegionProfile


def target_family(famille: str) -> str:
    """Famille cible : CSRS par défaut (WGS84/NAD27/autre/indéfini), sinon préservée."""
    return famille if famille in {"csrs", "nad83"} else "csrs"


def fuseau_par_zone(profile: RegionProfile, zone: int) -> Fuseau:
    """Fuseau du profil correspondant au numéro de zone donné."""
    for fuseau in profile.fuseaux:
        if fuseau.zone == zone:
            return fuseau
    raise KeyError(zone)


def zone_epsg(fuseau: Fuseau, target: str) -> int:
    """Code EPSG du fuseau pour la famille cible ; refuse si la famille n'a pas de code (DT-18)."""
    code = {"csrs": fuseau.epsg_csrs, "nad83": fuseau.epsg_nad83}.get(target)
    if code is None:
        raise UnknownRegionError(msg.zone_sans_code_famille(fuseau.zone, target))
    return code


def lambert_epsg(profile: RegionProfile, target: str) -> int:
    """Code EPSG du CRS multi-zones pour la famille cible ; refuse si absent (DT-18)."""
    code = profile.multi_zones.get(target)
    if code is None:
        raise UnknownRegionError(msg.multi_zones_sans_code_famille(profile.id, target))
    return code


def libelle_crs(epsg: int) -> str:
    """Nom pyproj du CRS pour un code EPSG donné."""
    return CRS.from_epsg(epsg).name
