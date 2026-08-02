"""Tests de la génération de grille (core/gridgen.build_grid) — TP-30 à TP-32.

build_grid est pur : il reçoit un RegionProfile et une emprise (GeoDataFrame),
et ne lit aucun fichier (loi de dépendance §3). Les cas zz utilisent une emprise
fictive ; TP-30/32 utilisent le profil qc réel et sa limite committée.
"""

from pathlib import Path

import geopandas as gpd
import pytest
from pandas.testing import assert_frame_equal

import crs_zone_toolkit
from crs_zone_toolkit.core.gridgen import build_grid
from crs_zone_toolkit.regions.loader import load_boundary, load_profile

GRILLE_QC = (
    Path(crs_zone_toolkit.__file__).resolve().parent / "regions" / "qc" / "grille_mtm_qc.geojson"
)

COLONNES = {
    "zone",
    "epsg_csrs",
    "epsg_nad83",
    "epsg_nad27",
    "meridien_central",
    "lon_min",
    "lon_max",
    "geometry",
}


def test_grille_no_clip_bandes_completes_zz(
    zz_regions_dir: object, zz_boundary: gpd.GeoDataFrame
) -> None:
    profile = load_profile("zz", regions_dir=zz_regions_dir)  # type: ignore[arg-type]
    grille = build_grid(profile, zz_boundary, clip=False)

    assert len(grille) == 2
    assert set(grille.columns) >= COLONNES
    assert sorted(grille["zone"]) == [1, 2]
    assert grille["epsg_csrs"].tolist() == [99991, 99992]
    # Bande 1 : rectangle lon 0..1 borné en latitude par l'emprise (10..12).
    bande1 = grille.loc[grille["zone"] == 1].total_bounds
    assert list(bande1) == pytest.approx([0.0, 10.0, 1.0, 12.0])


def test_grille_clip_reduit_les_bandes_zz(
    zz_regions_dir: object, zz_boundary_etroit: gpd.GeoDataFrame
) -> None:
    profile = load_profile("zz", regions_dir=zz_regions_dir)  # type: ignore[arg-type]
    pleine = build_grid(profile, zz_boundary_etroit, clip=False)
    coupee = build_grid(profile, zz_boundary_etroit, clip=True)

    for zone in (1, 2):
        geom_pleine = pleine.loc[pleine["zone"] == zone].geometry.iloc[0]
        geom_coupee = coupee.loc[coupee["zone"] == zone].geometry.iloc[0]
        assert geom_coupee.within(geom_pleine.buffer(1e-9))
        assert geom_coupee.area < geom_pleine.area


def test_grille_qc_defaut_tp30() -> None:
    profile = load_profile("qc")
    boundary = load_boundary(profile)
    grille = build_grid(profile, boundary, clip=True)

    assert len(grille) == 9
    assert sorted(grille["zone"]) == [2, 3, 4, 5, 6, 7, 8, 9, 10]
    # epsg_nad27 non nul pour les fuseaux 2–6 seulement (DATA_REFERENCE §2).
    avec_nad27 = set(grille.loc[grille["epsg_nad27"].notna(), "zone"])
    assert avec_nad27 == {2, 3, 4, 5, 6}
    # Géométries découpées incluses dans les bandes complètes.
    pleine = build_grid(profile, boundary, clip=False)
    for zone in grille["zone"]:
        geom_coupee = grille.loc[grille["zone"] == zone].geometry.iloc[0]
        geom_pleine = pleine.loc[pleine["zone"] == zone].geometry.iloc[0]
        assert geom_coupee.within(geom_pleine.buffer(1e-9))


def test_grille_committee_identique_a_regeneree_tp32(tmp_path: Path) -> None:
    profile = load_profile("qc")
    boundary = load_boundary(profile)
    regeneree = build_grid(profile, boundary, clip=True)

    # On round-trip la grille régénérée par GeoJSON pour comparer à égalité de
    # types/précision avec la version committée (elle-même écrite par to_file).
    regen_path = tmp_path / "regen.geojson"
    regeneree.to_file(regen_path, driver="GeoJSON")
    a = gpd.read_file(regen_path).sort_values("zone").reset_index(drop=True)
    b = gpd.read_file(GRILLE_QC).sort_values("zone").reset_index(drop=True)

    assert_frame_equal(a.drop(columns="geometry"), b.drop(columns="geometry"), check_dtype=False)
    assert a.geometry.geom_equals_exact(b.geometry, tolerance=1e-9).all()
