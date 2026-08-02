"""Types du profil de région, partagés par le noyau (dataclasses gelées).

Définis dans le noyau pour que analysis/apply/gridgen les reçoivent sans dépendre
de regions/ (loi de dépendance ARCHITECTURE §3). Le loader (regions/) les remplit
à partir de profil.toml ; le noyau ne connaît aucune valeur régionale — seulement
la forme de ces données. Aucun littéral géodésique ici (TP-40).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Seuils:
    """Seuils de la règle de décision (SPEC §4.3) — calibrés par région."""

    part_dominante_min: float
    distorsion_max_ppm: float
    n_echantillons: int


@dataclass(frozen=True)
class Fuseau:
    """Une bande de fuseau et ses codes EPSG par famille de datum (DATA_REFERENCE §2)."""

    zone: int
    meridien_central: float
    lon_min: float
    lon_max: float
    epsg_csrs: int
    epsg_nad83: int | None = None
    epsg_nad27: int | None = None


@dataclass(frozen=True)
class Reconnu:
    """CRS « en circulation » reconnu en entrée sans être recommandé (DATA_REFERENCE §4.2)."""

    codes: tuple[int, ...]
    etiquette: str


@dataclass(frozen=True)
class RegionProfile:
    """Profil de région validé, injecté dans le noyau (feuille de route §1.1–1.2)."""

    id: str
    nom: str
    version: str
    grille: str
    limite: str
    seuils: Seuils
    famille_defaut: str
    familles_grille_obligatoire: tuple[str, ...]
    """Familles de datum exigeant une transformation EXACTE par grille (DT-01).

    Pour ces familles, une transformation approximative (« ballpark ») est
    refusée (DATA_REFERENCE §1.5 / §6.1) ; pour les autres, elle est acceptée
    mais avertie et journalisée. `()` = aucune famille à risque déclarée.
    """
    geographiques: dict[str, int]
    multi_zones: dict[str, int]
    fuseaux: tuple[Fuseau, ...]
    reconnus: tuple[Reconnu, ...] = ()
    etiquette_multi_zones: str | None = None
    """Libellé d'affichage du CRS multi-zones (donnée régionale — le nom pyproj sert de repli)."""
