"""Génération de la grille des fuseaux depuis un RegionProfile (bandes + découpe).

Contrats : docs/SPEC.md §6, docs/DATA_REFERENCE.md §6.2. La grille committée
dans regions/qc/ doit rester identique à la grille régénérée (TP-32).

build_grid est PUR (loi de dépendance §3) : il reçoit le profil et l'emprise
(GeoDataFrame injecté par le loader), ne lit aucun fichier, et ne connaît aucune
valeur géodésique — tous les codes EPSG viennent du profil (TP-40).
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
from shapely.geometry import box

from crs_zone_toolkit.core.profile import RegionProfile

# Attributs par cellule (SPEC §6) — ordre stable pour la reproductibilité (TP-32).
_ATTRIBUTS = (
    "zone",
    "epsg_csrs",
    "epsg_nad83",
    "epsg_nad27",
    "meridien_central",
    "lon_min",
    "lon_max",
)


def build_grid(
    profile: RegionProfile, boundary: gpd.GeoDataFrame, *, clip: bool = True
) -> gpd.GeoDataFrame:
    """Construit la grille des fuseaux du profil, bornée en latitude par l'emprise.

    - clip=False : bandes rectangulaires complètes (lon du fuseau × latitude de
      l'emprise), SPEC §6 « --no-clip ».
    - clip=True (défaut) : bandes découpées sur l'emprise du Québec.

    Les fuseaux sont triés par numéro ; une cellule vide après découpe est écartée.
    Le CRS de sortie est celui de l'emprise.
    """
    _minx, miny, _maxx, maxy = (float(v) for v in boundary.total_bounds)
    emprise = boundary.geometry.union_all() if clip else None

    colonnes: dict[str, list[Any]] = {attribut: [] for attribut in _ATTRIBUTS}
    geometries: list[Any] = []
    for fuseau in sorted(profile.fuseaux, key=lambda f: f.zone):
        bande = box(fuseau.lon_min, miny, fuseau.lon_max, maxy)
        geometrie = bande.intersection(emprise) if clip else bande
        if geometrie.is_empty:
            continue
        colonnes["zone"].append(fuseau.zone)
        colonnes["epsg_csrs"].append(fuseau.epsg_csrs)
        colonnes["epsg_nad83"].append(fuseau.epsg_nad83)
        colonnes["epsg_nad27"].append(fuseau.epsg_nad27)
        colonnes["meridien_central"].append(fuseau.meridien_central)
        colonnes["lon_min"].append(fuseau.lon_min)
        colonnes["lon_max"].append(fuseau.lon_max)
        geometries.append(geometrie)

    return gpd.GeoDataFrame(colonnes, geometry=geometries, crs=boundary.crs)
