"""TP-33 — la sortie JSON (§8) valide contre un schéma versionné dans tests/.

Note : pas de cas dédié par `action` ("aucune"/"zone"/"split"/"lambert") ici —
le schéma les couvre structurellement via son enum, et le rendu par action est
déjà testé côté rapport (tests/test_report_render.py). Dupliquer un GeoJSON par
action rien que pour la validation de schéma serait de faible valeur ajoutée.
"""

import json
from pathlib import Path

import jsonschema
import pytest

import crs_zone_toolkit

SCHEMA_PATH = Path(__file__).parent / "schemas" / "analyse_v1.schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_sortie_analyze_valide_contre_schema(schema, tmp_path) -> None:
    import geopandas as gpd
    from shapely.geometry import LineString

    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    src = tmp_path / "routes.geojson"
    gpd.GeoDataFrame(geometry=lignes, crs=4326).to_file(src, driver="GeoJSON")

    result = crs_zone_toolkit.analyze(src)
    sortie = result.to_dict()
    jsonschema.validate(instance=sortie, schema=schema)  # ne lève pas
    assert sortie["schema_version"] == 1


def test_schema_rejette_json_tronque(schema) -> None:
    """Test négatif : un JSON amputé d'une clé requise échoue la validation."""
    incomplet = {"schema_version": 1, "couche": "x"}  # manque le reste
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=incomplet, schema=schema)
