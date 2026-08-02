"""Journal de décision (SPEC §9) — structure vérifiable sur le JSON."""

import json
from pathlib import Path

from crs_zone_toolkit.core.apply import _write_journal
from crs_zone_toolkit.core.results import Decision, FichierProduit


class _Reco:
    action, cible_epsg = "lambert", 6622

    def _asdict(self):
        return {"action": "lambert", "cible_epsg": 6622}


class _Analyse:
    famille = "wgs84"
    recommandation = _Reco()

    def to_dict(self):
        return {
            "schema_version": 1,
            "famille": "wgs84",
            "recommandation": {"action": "lambert", "cible_epsg": 6622},
        }


def test_journal_structure_et_note_choix(tmp_path: Path) -> None:
    fichiers = (FichierProduit(str(tmp_path / "c_zone9_epsg2951.gpkg"), 2951, 9, 10),)
    chemin = _write_journal(
        tmp_path,
        "c",
        _Analyse(),
        Decision("zone", "choice", zone=9),
        2951,
        ("pipeline…",),
        fichiers,
        [],
    )
    data = json.loads(Path(chemin).read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["decision"]["origine"] == "choice"
    assert data["decision"]["note"] == "choix utilisateur ≠ recommandation"  # 2951 ≠ reco 6622
    assert data["pipeline_proj"] == ["pipeline…"]
    assert data["fichiers"][0]["epsg"] == 2951
    assert "horodatage" in data and "version_outil" in data
