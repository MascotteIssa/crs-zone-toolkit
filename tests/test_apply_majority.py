"""Affectation majoritaire : surface (polygones), longueur (lignes), position (points)."""

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon, box

from crs_zone_toolkit.core.apply import _assign_majority

# Grille factice 2 cellules contiguës, lon [0,1]/[1,2], lat [0,2] (mesure en 3857).
GRID = gpd.GeoDataFrame({"zone": [1, 2]}, geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)], crs=4326)
MEASURE = 3857


def test_polygone_majorite_surface_pas_centroide() -> None:
    # Croissant : ~70 % de surface en cellule 1, centroïde en cellule 2.
    poly = Polygon([(0.1, 0.5), (0.9, 0.2), (1.4, 1.0), (0.9, 1.8), (0.1, 1.5), (0.7, 1.0)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs=4326)
    groups, _ = _assign_majority(gdf, GRID, MEASURE)
    assert set(groups) == {1}  # affecté à la cellule de surface dominante
    assert len(groups[1]) == 1


def test_ligne_majorite_longueur() -> None:
    # 70 % de longueur en cellule 2.
    ligne = LineString([(0.7, 1.0), (2.0, 1.0)])
    gdf = gpd.GeoDataFrame(geometry=[ligne], crs=4326)
    groups, _ = _assign_majority(gdf, GRID, MEASURE)
    assert set(groups) == {2}


def test_points_par_position_et_conservation() -> None:
    pts = [Point(0.5, 1), Point(0.4, 1), Point(1.5, 1)]
    gdf = gpd.GeoDataFrame(geometry=pts, crs=4326)
    groups, _ = _assign_majority(gdf, GRID, MEASURE)
    assert len(groups[1]) == 2 and len(groups[2]) == 1
    assert sum(len(g) for g in groups.values()) == 3  # aucune entité perdue
