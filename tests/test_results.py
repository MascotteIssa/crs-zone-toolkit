"""Contrat de sérialisation d'AnalysisResult (SPEC §8)."""

import json

from crs_zone_toolkit.core.results import (
    SCHEMA_VERSION,
    AnalysisResult,
    Distorsion,
    Emprise,
    Recommandation,
    ZonePart,
)


def _exemple() -> AnalysisResult:
    return AnalysisResult(
        schema_version=SCHEMA_VERSION,
        couche="essai",
        crs_entree={"epsg": 4326, "etiquette": "WGS 84", "suppose": False, "reconnu": None},
        famille="wgs84",
        type_geometrie="point",
        emprise=Emprise(-72.0, 45.3, -71.5, 45.6),
        zones_traversees=(ZonePart(zone=7, epsg=2949, part=1.0),),
        part_hors_profil=0.0,
        distorsions=(Distorsion("MTM fuseau 7", 2949, -101.0, -80.0, -60.0),),
        recommandation=Recommandation(
            "zone", 2949, "MTM fuseau 7", "mono_zone", "un seul fuseau", ()
        ),
        avertissements=(),
        parametres={
            "region": "qc",
            "n_echantillons": 200,
            "part_dominante_min": 0.9,
            "distorsion_max_ppm": 200,
        },
    )


def test_to_json_respecte_les_cles_spec_8() -> None:
    data = json.loads(_exemple().to_json())
    assert data["schema_version"] == SCHEMA_VERSION
    assert set(data) >= {
        "schema_version",
        "couche",
        "crs_entree",
        "famille",
        "type_geometrie",
        "emprise",
        "zones_traversees",
        "part_hors_profil",
        "distorsion",
        "recommandation",
        "avertissements",
        "parametres",
    }
    assert data["zones_traversees"][0] == {"zone": 7, "epsg": 2949, "part": 1.0}
    assert data["recommandation"]["cible_epsg"] == 2949
    assert data["recommandation"]["motif_code"] == "mono_zone"
    assert data["distorsion"]["2949"]["min_ppm"] == -101.0


def test_dataclasses_sont_gelees() -> None:
    import dataclasses

    import pytest

    zp = ZonePart(zone=7, epsg=2949, part=1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        zp.part = 0.5  # type: ignore[misc]


def test_apply_result_to_json() -> None:
    import json

    from crs_zone_toolkit.core.results import ApplyResult, FichierProduit

    r = ApplyResult(
        fichiers=(FichierProduit("out/x_epsg2949.gpkg", 2949, None, 50),),
        pipeline_proj=("+proj=pipeline …",),
        journal="out/x_journal.json",
        avertissements=(),
    )
    data = json.loads(r.to_json())
    assert data["fichiers"][0] == {
        "chemin": "out/x_epsg2949.gpkg",
        "epsg": 2949,
        "zone": None,
        "n_entites": 50,
    }
    assert data["journal"].endswith("_journal.json")


def test_decision_defaut_zone_none() -> None:
    from crs_zone_toolkit.core.results import Decision

    d = Decision(choix="split", origine="choice")
    assert d.zone is None
