"""Cas TP-01 à TP-13 : détection et recommandation (analyze noyau, assertions JSON)."""

import dataclasses
import json

import geopandas as gpd
import pytest
from pyproj import CRS
from shapely.geometry import GeometryCollection, LineString, Point, Polygon

from crs_zone_toolkit.core.analysis import analyze
from crs_zone_toolkit.core.errors import EmptyLayerError, InvalidGeometryError, MissingCrsError


def _json(layer: gpd.GeoDataFrame, profile, grid, **kw) -> dict:
    return json.loads(analyze(layer, "essai", profile=profile, grid=grid, **kw).to_json())


def test_tp01_mono_fuseau_7(tp01_points_fuseau7, qc_profile, qc_grid) -> None:
    data = _json(tp01_points_fuseau7, qc_profile, qc_grid)
    assert data["famille"] == "wgs84"
    assert data["recommandation"]["action"] == "zone"
    assert data["recommandation"]["cible_epsg"] == 2949  # fuseau 7 CSRS (entrée WGS84)
    assert data["recommandation"]["motif_code"] == "mono_zone"
    zones = {z["zone"]: z["part"] for z in data["zones_traversees"]}
    assert zones == {7: 1.0}


def test_tp02_deux_fuseaux_mtm_moins_deforme(tp02_lignes_deux_fuseaux, qc_profile, qc_grid) -> None:
    # 2 fuseaux compacts : le fuseau dominant (MTM 9) est MOINS déformé que le
    # Lambert, mais dépasse la tolérance → titre = fuseau, découpage offert (B2, §4.3).
    data = _json(tp02_lignes_deux_fuseaux, qc_profile, qc_grid)
    assert data["recommandation"]["action"] == "zone"
    assert data["recommandation"]["cible_epsg"] == 2951  # fuseau 9 CSRS (entrée WGS84)
    assert data["recommandation"]["motif_code"] == "zone_moins_deformee"
    zones = {z["zone"]: z["part"] for z in data["zones_traversees"]}
    assert abs(zones[9] - 0.58) <= 0.02 and abs(zones[8] - 0.42) <= 0.02
    actions = {alt["action"] for alt in data["recommandation"]["alternatives"]}
    # N20/N23 (2026-08-02) : les entités de ce cas sont TOUTES majoritaires dans le
    # même fuseau — le découpage rendrait un fichier unique, identique à une
    # reprojection vers ce fuseau. L'alternative n'est donc plus proposée, et le motif
    # ne promet plus qu'elle « garde chaque morceau sous le seuil » (SPEC §4.3 point 3,
    # amendé). Le cas où le découpage sert reste couvert par TP-04 (points, deux fuseaux
    # majoritaires), TP-21 et tests/test_decide_decoupage_utile.py.
    assert "split" not in actions


def test_tp03_quatre_fuseaux_vers_lambert(
    tp03_polygones_quatre_fuseaux, qc_profile, qc_grid
) -> None:
    # 4 fuseaux étalés : même le fuseau dominant se déforme plus que le Lambert
    # → Lambert (projection unique la moins déformée), découpage offert (B2, §4.3).
    data = _json(tp03_polygones_quatre_fuseaux, qc_profile, qc_grid)
    assert data["recommandation"]["action"] == "lambert"
    assert data["recommandation"]["motif_code"] == "lambert_moins_deforme"
    zones = {z["zone"] for z in data["zones_traversees"]}
    assert {7, 8, 9, 10} <= zones
    actions = {alt["action"] for alt in data["recommandation"]["alternatives"]}
    # N20/N23 (2026-08-02) : les entités de ce cas sont TOUTES majoritaires dans le
    # même fuseau — le découpage rendrait un fichier unique, identique à une
    # reprojection vers ce fuseau. L'alternative n'est donc plus proposée, et le motif
    # ne promet plus qu'elle « garde chaque morceau sous le seuil » (SPEC §4.3 point 3,
    # amendé). Le cas où le découpage sert reste couvert par TP-04 (points, deux fuseaux
    # majoritaires), TP-21 et tests/test_decide_decoupage_utile.py.
    assert "split" not in actions
    # DT-20 n°1 : le libellé du CRS multi-zones vient du profil (« Québec Lambert »),
    # jamais du nom brut pyproj — recommandation ET candidat de distorsion.
    assert data["recommandation"]["cible_libelle"] == "Québec Lambert"
    lambert_epsg = str(data["recommandation"]["cible_epsg"])
    assert data["distorsion"][lambert_epsg]["libelle"] == "Québec Lambert"


def test_libelle_lambert_repli_pyproj_si_profil_sans_etiquette(
    tp03_polygones_quatre_fuseaux, qc_profile, qc_grid
) -> None:
    """TP-41 : un profil sans `etiquette_multi_zones` garde le nom pyproj (repli)."""
    profil_sans_etiquette = dataclasses.replace(qc_profile, etiquette_multi_zones=None)
    data = _json(tp03_polygones_quatre_fuseaux, profil_sans_etiquette, qc_grid)
    assert data["recommandation"]["action"] == "lambert"
    lambert_epsg = data["recommandation"]["cible_epsg"]
    attendu = CRS.from_epsg(lambert_epsg).name
    assert data["recommandation"]["cible_libelle"] == attendu
    assert data["distorsion"][str(lambert_epsg)]["libelle"] == attendu
    assert data["recommandation"]["cible_libelle"] != "Québec Lambert"


def test_guard_hors_profil_total_ne_plante_pas(
    hors_profil_total_points, qc_profile, qc_grid
) -> None:
    """Couche entièrement hors profil (aucun fuseau touché) : pas d'IndexError, action='aucune'."""
    data = _json(hors_profil_total_points, qc_profile, qc_grid)
    assert data["zones_traversees"] == []
    assert data["recommandation"]["action"] == "aucune"
    assert data["recommandation"]["motif_code"] == "hors_profil"


def test_tp04_fuseau_dominant(tp04_dominant_fuseau8_distorsion_ok, qc_profile, qc_grid) -> None:
    # dominant compact, fuseau sous la tolérance → MTM, découpage toujours offert (a).
    data = _json(tp04_dominant_fuseau8_distorsion_ok, qc_profile, qc_grid)
    assert data["recommandation"]["action"] == "zone"
    assert data["recommandation"]["cible_epsg"] == 2950  # fuseau 8 CSRS
    assert data["recommandation"]["motif_code"] == "zone_dominante"
    actions = {alt["action"] for alt in data["recommandation"]["alternatives"]}
    assert "split" in actions


def test_tp05_lambert_moins_deforme(
    tp05_dominant_fuseau8_distorsion_ko, qc_profile, qc_grid
) -> None:
    # dominant à 91 % mais très étalé : le fuseau dominant se déforme PLUS que le
    # Lambert → Lambert (moins déformé). Le portillon de part ne gate plus (B2).
    data = _json(tp05_dominant_fuseau8_distorsion_ko, qc_profile, qc_grid)
    assert data["recommandation"]["action"] == "lambert"
    assert data["recommandation"]["motif_code"] == "lambert_moins_deforme"


def test_tp07_nad83_origine_preserve(tp07_lignes_nad83_origine, qc_profile, qc_grid) -> None:
    # Famille préservée : entrée NAD83 d'origine → cible en codes NAD83, jamais CSRS.
    # TP-02 en 4269 recommande le fuseau (B2) → MTM 9 NAD83 (32189), pas 2951.
    data = _json(tp07_lignes_nad83_origine, qc_profile, qc_grid)
    assert data["famille"] == "nad83"
    assert data["recommandation"]["cible_epsg"] == 32189  # MTM 9 NAD83 (famille préservée)
    # DT-26 : la note « NAD83(CSRS) est le standard actuel » reste dite, mais elle
    # a quitté les AVERTISSEMENTS. Une famille préservée est le cas le moins
    # risqué : lui laisser un ⚠ pendant qu'un changement de famille n'en recevait
    # aucun inversait la hiérarchie. La chaîne, elle, est inchangée.
    from crs_zone_toolkit.core import messages as _msg

    assert data["avertissements"] == []
    assert "CSRS" in (_msg.analyse_note_datum("nad83") or "")


def test_tp08_nad27_cible_csrs_avec_ntv2(tp08_points_nad27_fuseau4, qc_profile, qc_grid) -> None:
    data = _json(tp08_points_nad27_fuseau4, qc_profile, qc_grid)
    assert data["famille"] == "nad27"
    assert data["recommandation"]["cible_epsg"] == 2946  # fuseau 4 CSRS (NAD27→CSRS)
    assert any("NTv2" in a for a in data["avertissements"])


def test_tp09_scopq_zone2_reconnu(tp09_points_scopq_zone2, qc_profile, qc_grid) -> None:
    data = _json(tp09_points_scopq_zone2, qc_profile, qc_grid)
    assert data["crs_entree"]["reconnu"] == "SCoPQ zone 2"


def test_tp10_mtq_lambert_distingue(tp10_points_mtq_lambert, qc_profile, qc_grid) -> None:
    data = _json(tp10_points_mtq_lambert, qc_profile, qc_grid)
    assert data["crs_entree"]["reconnu"] == "MTQ Lambert"
    assert "Québec Lambert" not in data["crs_entree"]["etiquette"]  # distinct du Québec Lambert


def test_tp11_partiellement_hors_profil(
    tp11_points_partiellement_hors, qc_profile, qc_grid
) -> None:
    data = _json(tp11_points_partiellement_hors, qc_profile, qc_grid)
    assert abs(data["part_hors_profil"] - 0.15) <= 0.03
    assert any("hors du profil" in a for a in data["avertissements"])


def test_tp06_sans_crs_leve(tp06_sans_crs, qc_profile, qc_grid) -> None:
    with pytest.raises(MissingCrsError):
        analyze(tp06_sans_crs, "essai", profile=qc_profile, grid=qc_grid)


def test_tp06_assume_crs_suppose(tp06_sans_crs, qc_profile, qc_grid) -> None:
    data = _json(tp06_sans_crs, qc_profile, qc_grid, assume_crs="EPSG:2950")
    assert data["crs_entree"]["suppose"] is True
    assert any("supposé" in a.lower() for a in data["avertissements"])


def test_tp12_couche_vide(qc_profile, qc_grid) -> None:
    vide = gpd.GeoDataFrame(geometry=[], crs=4326)
    with pytest.raises(EmptyLayerError):
        analyze(vide, "essai", profile=qc_profile, grid=qc_grid)


def test_tp13_papillon_repare(tp13_polygone_papillon, qc_profile, qc_grid) -> None:
    data = _json(tp13_polygone_papillon, qc_profile, qc_grid)
    assert any("make_valid" in a.lower() or "réparé" in a.lower() for a in data["avertissements"])
    assert data["recommandation"]["action"] in {"zone", "lambert"}  # l'analyse aboutit


def test_tp13_geometrie_irreparable_leve(couche_geometrie_irreparable, qc_profile, qc_grid) -> None:
    """Un lot avec un polygone déjà vide reste vide après make_valid → InvalidGeometryError (M3)."""
    with pytest.raises(InvalidGeometryError):
        analyze(couche_geometrie_irreparable, "essai", profile=qc_profile, grid=qc_grid)


def test_multipoint_ne_plante_pas(multipoint_layer, qc_profile, qc_grid) -> None:
    """MultiPoint n'a ni .x ni .y : _sample_lonlat ne doit pas lever d'AttributeError (I1)."""
    data = _json(multipoint_layer, qc_profile, qc_grid)
    assert data["recommandation"] is not None
    assert data["recommandation"]["action"] in {"zone", "lambert", "aucune"}


def test_analyze_geometrycollection_majorite_polygones(qc_profile, qc_grid) -> None:
    """DT-09 (crash GC) : une GC dans une couche à majorité polygones n'interrompt pas l'analyse."""
    carre = Polygon([(-71.6, 45.4), (-71.5, 45.4), (-71.5, 45.5), (-71.6, 45.5)])
    gc = GeometryCollection(
        [Polygon([(-71.4, 45.4), (-71.3, 45.4), (-71.3, 45.5)]), Point(-71.35, 45.45)]
    )
    layer = gpd.GeoDataFrame(geometry=[carre, gc], crs=4326)
    result = analyze(layer, "gc_poly", profile=qc_profile, grid=qc_grid)
    assert result.recommandation.action == "zone"
    assert result.parametres["n_echantillons_effectif"] > 0


def test_analyze_geometrycollection_majorite_lignes(qc_profile, qc_grid) -> None:
    """DT-09 (crash GC, chemin jumeau) : une GC dans une couche à majorité de lignes."""
    l1 = LineString([(-76.4, 46.0), (-76.2, 46.0)])
    l2 = LineString([(-76.4, 46.1), (-76.2, 46.1)])
    l3 = LineString([(-76.4, 46.2), (-76.2, 46.2)])
    gc = GeometryCollection([Point(-76.3, 46.05), LineString([(-76.35, 46.15), (-76.25, 46.15)])])
    layer = gpd.GeoDataFrame(geometry=[l1, l2, l3, gc], crs=4326)
    result = analyze(layer, "gc_lignes", profile=qc_profile, grid=qc_grid)
    assert result.recommandation.action == "zone"
