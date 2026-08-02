"""Dataclasses gelées de résultat du moteur (feuille du noyau, comme profile.py).

to_json() est le contrat SPEC §8 : clés françaises, distorsion indexée par code
EPSG candidat. report.py/apply.py importent ces types sans dépendre du moteur.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Emprise:
    """Boîte englobante des données en degrés WGS84."""

    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float


@dataclass(frozen=True)
class ZonePart:
    """Part des données tombant dans un fuseau (grandeur dominante du type géom.)."""

    zone: int
    epsg: int
    part: float


@dataclass(frozen=True)
class Distorsion:
    """Facteurs d'échelle linéaires (ppm) d'un CRS candidat sur l'échantillon."""

    libelle: str
    epsg: int
    min_ppm: float
    moy_ppm: float
    max_ppm: float


@dataclass(frozen=True)
class Recommandation:
    """Recommandation chiffrée (jamais un verdict sec) — SPEC §4.3."""

    action: str  # "zone" | "lambert" | "aucune"
    cible_epsg: int
    cible_libelle: str
    motif_code: (
        str  # mono_zone|zone_dominante|zone_moins_deformee|lambert_moins_deforme|hors_profil
    )
    motif: str
    alternatives: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class AnalysisResult:
    """Résultat complet d'`analyze` — sérialisable (SPEC §8), injecté dans report/apply."""

    schema_version: int
    couche: str
    crs_entree: dict[str, Any]
    famille: str
    type_geometrie: str
    emprise: Emprise
    zones_traversees: tuple[ZonePart, ...]
    part_hors_profil: float
    distorsions: tuple[Distorsion, ...]
    recommandation: Recommandation
    avertissements: tuple[str, ...]
    parametres: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Mapping JSON du contrat SPEC §8 (clés françaises)."""
        return {
            "schema_version": self.schema_version,
            "couche": self.couche,
            "crs_entree": self.crs_entree,
            "famille": self.famille,
            "type_geometrie": self.type_geometrie,
            "emprise": {
                "lon_min": self.emprise.lon_min,
                "lat_min": self.emprise.lat_min,
                "lon_max": self.emprise.lon_max,
                "lat_max": self.emprise.lat_max,
            },
            "zones_traversees": [
                {"zone": z.zone, "epsg": z.epsg, "part": z.part} for z in self.zones_traversees
            ],
            "part_hors_profil": self.part_hors_profil,
            "distorsion": {
                str(d.epsg): {
                    "libelle": d.libelle,
                    "min_ppm": d.min_ppm,
                    "moy_ppm": d.moy_ppm,
                    "max_ppm": d.max_ppm,
                }
                for d in self.distorsions
            },
            "recommandation": {
                "action": self.recommandation.action,
                "cible_epsg": self.recommandation.cible_epsg,
                "cible_libelle": self.recommandation.cible_libelle,
                "motif_code": self.recommandation.motif_code,
                "motif": self.recommandation.motif,
                "alternatives": list(self.recommandation.alternatives),
            },
            "avertissements": list(self.avertissements),
            "parametres": self.parametres,
        }

    def to_json(self) -> str:
        """Sérialisation JSON (contrat SPEC §8)."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass(frozen=True)
class Decision:
    """Décision d'exécution passée à apply (ARCHITECTURE §4)."""

    choix: str  # "recommendation" | "zone" | "lambert" | "split"
    origine: str  # "auto" | "choice" | "interactive"
    zone: int | None = None


@dataclass(frozen=True)
class FichierProduit:
    """Un fichier écrit par apply, avec son CRS final et son effectif."""

    chemin: str
    epsg: int
    zone: int | None
    n_entites: int


@dataclass(frozen=True)
class ApplyResult:
    """Résultat d'apply — fichiers produits, pipeline PROJ, journal (SPEC §9)."""

    fichiers: tuple[FichierProduit, ...]
    pipeline_proj: tuple[str, ...]
    journal: str
    avertissements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fichiers": [
                {"chemin": f.chemin, "epsg": f.epsg, "zone": f.zone, "n_entites": f.n_entites}
                for f in self.fichiers
            ],
            "pipeline_proj": list(self.pipeline_proj),
            "journal": self.journal,
            "avertissements": list(self.avertissements),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
