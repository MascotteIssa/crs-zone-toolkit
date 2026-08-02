"""Type de géométrie, échantillonnage, répartition par fuseau (SPEC §4.2.3)."""

import geopandas as gpd
from shapely.geometry import LineString, Point, box

from crs_zone_toolkit.core.analysis import _geometry_kind, _repartition, _sample_lonlat

# Grille factice : 2 cellules contiguës en lon [0,1] et [1,2], lat [0,2].
GRID = gpd.GeoDataFrame({"zone": [1, 2]}, geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)], crs=4326)

# CRS de mesure des tests synthétiques : Web Mercator (3857). Près de l'équateur
# (lat 0–2), x = R·lon exactement → les parts axiales restent exactes (0,5 ; 0,75…).
MEASURE = 3857


def test_kind_points() -> None:
    gdf = gpd.GeoDataFrame(geometry=[Point(0.5, 1), Point(1.5, 1)], crs=4326)
    assert _geometry_kind(gdf) == "point"


def test_kind_lignes() -> None:
    gdf = gpd.GeoDataFrame(geometry=[LineString([(0, 1), (2, 1)])], crs=4326)
    assert _geometry_kind(gdf) == "line"


def test_repartition_points_par_effectif() -> None:
    # 3 points en cellule 1, 1 point en cellule 2 → 75 % / 25 %.
    pts = [Point(0.5, 1), Point(0.4, 1), Point(0.6, 1), Point(1.5, 1)]
    gdf = gpd.GeoDataFrame(geometry=pts, crs=4326)
    zones, hors = _repartition(gdf, GRID, "point", MEASURE)
    assert hors == 0.0
    assert dict(zones)[1] == 0.75
    assert dict(zones)[2] == 0.25
    assert zones[0][0] == 1  # trié : dominant en tête


def test_repartition_points_hors_profil() -> None:
    # 3 dans la grille, 1 hors (lon 5) → 25 % hors.
    pts = [Point(0.5, 1), Point(0.6, 1), Point(1.5, 1), Point(5.0, 1)]
    gdf = gpd.GeoDataFrame(geometry=pts, crs=4326)
    _zones, hors = _repartition(gdf, GRID, "point", MEASURE)
    assert round(hors, 2) == 0.25


def test_repartition_ligne_par_longueur() -> None:
    # Ligne horizontale 0→2 : moitié dans chaque cellule.
    gdf = gpd.GeoDataFrame(geometry=[LineString([(0, 1), (2, 1)])], crs=4326)
    zones, hors = _repartition(gdf, GRID, "line", MEASURE)
    assert round(hors, 6) == 0.0
    assert round(dict(zones)[1], 2) == 0.5


def test_sample_lonlat_plafonne_a_n() -> None:
    """Les 50 points tombent tous dans la cellule 1 : le plafond est bien la seule
    réduction à l'œuvre, l'exclusion hors profil (DT-24) n'en écarte aucun."""
    pts = [Point(i / 100, 1) for i in range(50)]
    gdf = gpd.GeoDataFrame(geometry=pts, crs=4326)
    lons, lats = _sample_lonlat(gdf, "point", 10, grid=GRID)
    assert len(lons) == len(lats) == 10


def test_sample_lonlat_ecarte_les_points_hors_grille() -> None:
    """DT-24 : la mesure ne porte que sur ce qui est dans le profil."""
    dedans = [Point(0.5, 1), Point(0.6, 1)]
    dehors = [Point(50.0, 50.0), Point(51.0, 51.0)]
    gdf = gpd.GeoDataFrame(geometry=[*dedans, *dehors], crs=4326)

    lons, lats = _sample_lonlat(gdf, "point", 10, grid=GRID)

    assert sorted(lons) == [0.5, 0.6]
    assert lats == [1.0, 1.0]


def test_sample_lonlat_tout_hors_grille_garde_l_echantillon_brut() -> None:
    """DT-24, garde : sans elle `_distortion` planterait sur une liste vide."""
    gdf = gpd.GeoDataFrame(geometry=[Point(50.0, 50.0), Point(51.0, 51.0)], crs=4326)

    lons, _ = _sample_lonlat(gdf, "point", 10, grid=GRID)

    assert sorted(lons) == [50.0, 51.0]
