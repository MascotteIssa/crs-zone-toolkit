"""Chargement et validation des profils de région (profil.toml) → RegionProfile.

Contrats : docs/ARCHITECTURE.md §2. Validation stricte au chargement (codes
EPSG entiers, bandes contiguës sans recouvrement, seuils dans ]0,1] / >0) :
un profil invalide lève UnknownRegionError, jamais un comportement silencieux.

Ce module ne connaît AUCUNE valeur géodésique : il lit celles du profil. Les
faits québécois vivent dans regions/qc/profil.toml (loi de dépendance §3).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import geopandas as gpd

from crs_zone_toolkit.core.errors import UnknownRegionError
from crs_zone_toolkit.core.profile import Fuseau, Reconnu, RegionProfile, Seuils


def load_profile(region: str, *, regions_dir: Path | None = None) -> RegionProfile:
    """Charge et valide le profil `region` depuis `<regions_dir>/<region>/profil.toml`.

    `regions_dir` par défaut = le dossier de ce module (regions/), où vivent les
    profils embarqués. Passer un autre dossier permet de charger un profil de
    test (le profil factice `zz`, TP-41) sans toucher au moteur.
    """
    base = regions_dir if regions_dir is not None else Path(__file__).resolve().parent
    profil_path = base / region / "profil.toml"
    if not profil_path.is_file():
        raise UnknownRegionError(
            f"Profil de région introuvable : {region!r} (attendu : {profil_path})"
        )
    try:
        with profil_path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise UnknownRegionError(f"Profil {region!r} illisible : {exc}") from exc
    return _build_profile(region, data)


def load_boundary(profile: RegionProfile, *, regions_dir: Path | None = None) -> gpd.GeoDataFrame:
    """Charge l'emprise (limite) du profil depuis `<regions_dir>/<id>/<limite>`.

    L'emprise sert à découper la grille et à borner en latitude les bandes
    complètes (SPEC §6, DATA_REFERENCE §6.2). Le noyau ne lit pas ce fichier
    lui-même (loi de dépendance §3) : il reçoit ce GeoDataFrame.
    """
    base = regions_dir if regions_dir is not None else Path(__file__).resolve().parent
    limite_path = base / profile.id / profile.limite
    if not limite_path.is_file():
        raise UnknownRegionError(
            f"[{profile.id}] emprise introuvable : {profile.limite} (attendu : {limite_path})"
        )
    try:
        return gpd.read_file(limite_path)
    except (OSError, ValueError) as exc:
        raise UnknownRegionError(f"[{profile.id}] emprise illisible : {exc}") from exc


def load_grid(profile: RegionProfile, *, regions_dir: Path | None = None) -> gpd.GeoDataFrame:
    """Charge la grille committée du profil (`<regions_dir>/<id>/<grille>`).

    La grille committée est la donnée de référence interne du moteur (SPEC §6).
    Le noyau ne la lit pas lui-même (loi §3) : il reçoit ce GeoDataFrame.
    """
    base = regions_dir if regions_dir is not None else Path(__file__).resolve().parent
    grille_path = base / profile.id / profile.grille
    if not grille_path.is_file():
        raise UnknownRegionError(
            f"[{profile.id}] grille introuvable : {profile.grille} (attendu : {grille_path})"
        )
    try:
        return gpd.read_file(grille_path)
    except (OSError, ValueError) as exc:
        raise UnknownRegionError(f"[{profile.id}] grille illisible : {exc}") from exc


# ── Construction validée ───────────────────────────────────────────────────


def _build_profile(region: str, data: dict[str, Any]) -> RegionProfile:
    profil = _section(data, "profil", region)
    datum = _section(data, "datum", region)
    geographiques = _int_map(
        _section(datum, "geographiques", region), region, "datum.geographiques"
    )
    multi_zones = _int_map(_section(data, "multi_zones", region), region, "multi_zones")
    if "csrs" not in multi_zones:
        raise UnknownRegionError(f"[{region}] multi_zones doit définir 'csrs'")
    return RegionProfile(
        id=_as_str(profil.get("id"), f"[{region}] profil.id"),
        nom=_as_str(profil.get("nom"), f"[{region}] profil.nom"),
        version=_as_str(profil.get("version"), f"[{region}] profil.version"),
        grille=_as_str(profil.get("grille"), f"[{region}] profil.grille"),
        limite=_as_str(profil.get("limite"), f"[{region}] profil.limite"),
        seuils=_build_seuils(_section(data, "seuils", region), region),
        famille_defaut=_as_str(datum.get("famille_defaut"), f"[{region}] datum.famille_defaut"),
        familles_grille_obligatoire=_build_familles_grille(
            datum.get("familles_grille_obligatoire"), region
        ),
        geographiques=geographiques,
        multi_zones=multi_zones,
        fuseaux=_build_fuseaux(data.get("fuseaux"), region),
        reconnus=_build_reconnus(data.get("reconnus_entree"), region),
        etiquette_multi_zones=_build_etiquette_multi_zones(profil, region),
    )


def _build_etiquette_multi_zones(profil: dict[str, Any], region: str) -> str | None:
    """Lecture optionnelle de `[profil].etiquette_multi_zones` (DT-20 n°1).

    Champ facultatif : un profil qui l'omet obtient `None` — le repli sur le nom
    pyproj vit dans le moteur (core/analysis.py), jamais ici (TP-41).
    """
    valeur = profil.get("etiquette_multi_zones")
    if valeur is None:
        return None
    return _as_str(valeur, f"[{region}] profil.etiquette_multi_zones")


def _build_seuils(raw: dict[str, Any], region: str) -> Seuils:
    part = _as_float(raw.get("part_dominante_min"), f"[{region}] seuils.part_dominante_min")
    if not 0.0 < part <= 1.0:
        raise UnknownRegionError(
            f"[{region}] seuils.part_dominante_min doit être dans ]0, 1], obtenu {part}"
        )
    distorsion = _as_float(raw.get("distorsion_max_ppm"), f"[{region}] seuils.distorsion_max_ppm")
    if distorsion <= 0:
        raise UnknownRegionError(
            f"[{region}] seuils.distorsion_max_ppm doit être > 0, obtenu {distorsion}"
        )
    n_echantillons = _as_int(raw.get("n_echantillons"), f"[{region}] seuils.n_echantillons")
    if n_echantillons <= 0:
        raise UnknownRegionError(
            f"[{region}] seuils.n_echantillons doit être > 0, obtenu {n_echantillons}"
        )
    return Seuils(
        part_dominante_min=part,
        distorsion_max_ppm=distorsion,
        n_echantillons=n_echantillons,
    )


def _build_fuseaux(raw: Any, region: str) -> tuple[Fuseau, ...]:
    if not isinstance(raw, list) or not raw:
        raise UnknownRegionError(f"[{region}] au moins un [[fuseaux]] est requis")
    fuseaux: list[Fuseau] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise UnknownRegionError(f"[{region}] fuseau #{index} : table attendue")
        ctx = f"[{region}] fuseau #{index}"
        lon_min = _as_float(item.get("lon_min"), f"{ctx} lon_min")
        lon_max = _as_float(item.get("lon_max"), f"{ctx} lon_max")
        if lon_min >= lon_max:
            raise UnknownRegionError(f"{ctx} : lon_min ({lon_min}) doit être < lon_max ({lon_max})")
        fuseaux.append(
            Fuseau(
                zone=_as_int(item.get("zone"), f"{ctx} zone"),
                meridien_central=_as_float(item.get("meridien_central"), f"{ctx} meridien_central"),
                lon_min=lon_min,
                lon_max=lon_max,
                epsg_csrs=_as_int(item.get("epsg_csrs"), f"{ctx} epsg_csrs"),
                epsg_nad83=_as_opt_int(item.get("epsg_nad83"), f"{ctx} epsg_nad83"),
                epsg_nad27=_as_opt_int(item.get("epsg_nad27"), f"{ctx} epsg_nad27"),
            )
        )
    _check_contiguous(fuseaux, region)
    return tuple(fuseaux)


def _build_familles_grille(raw: Any, region: str) -> tuple[str, ...]:
    """Valide `datum.familles_grille_obligatoire` — champ REQUIS (DT-01).

    Volontairement sans défaut permissif : un profil qui omettrait ce champ
    perdrait silencieusement la protection contre les transformations de datum
    approximatives (NAD27 au Québec). Une région sans famille à risque doit
    déclarer `[]` explicitement.
    """
    if not isinstance(raw, list):
        raise UnknownRegionError(
            f"[{region}] datum.familles_grille_obligatoire : liste de chaînes requise "
            "(familles de datum exigeant une transformation exacte par grille ; "
            "déclarer [] si aucune)"
        )
    return tuple(_as_str(f, f"[{region}] datum.familles_grille_obligatoire") for f in raw)


def _build_reconnus(raw: Any, region: str) -> tuple[Reconnu, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise UnknownRegionError(f"[{region}] reconnus_entree doit être une liste de tables")
    reconnus: list[Reconnu] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise UnknownRegionError(f"[{region}] reconnus_entree #{index} : table attendue")
        ctx = f"[{region}] reconnus_entree #{index}"
        codes_brut = item.get("codes")
        if not isinstance(codes_brut, list) or not codes_brut:
            raise UnknownRegionError(f"{ctx} : liste 'codes' non vide requise")
        codes = tuple(_as_int(code, f"{ctx} codes") for code in codes_brut)
        etiquette = _as_str(item.get("etiquette"), f"{ctx} etiquette")
        reconnus.append(Reconnu(codes=codes, etiquette=etiquette))
    return tuple(reconnus)


def _check_contiguous(fuseaux: list[Fuseau], region: str) -> None:
    ordered = sorted(fuseaux, key=lambda fuseau: fuseau.lon_min)
    for prev, following in zip(ordered, ordered[1:], strict=False):
        if abs(following.lon_min - prev.lon_max) > 1e-9:
            raise UnknownRegionError(
                f"[{region}] bandes non contiguës ou recouvrantes entre la zone "
                f"{prev.zone} (…{prev.lon_max}) et la zone {following.zone} ({following.lon_min}…)"
            )


# ── Extracteurs typés (toute anomalie → UnknownRegionError) ─────────────────


def _section(data: Any, name: str, region: str) -> dict[str, Any]:
    value = data.get(name) if isinstance(data, dict) else None
    if not isinstance(value, dict):
        raise UnknownRegionError(f"[{region}] section [{name}] manquante ou invalide")
    return value


def _int_map(raw: dict[str, Any], region: str, ctx: str) -> dict[str, int]:
    return {str(key): _as_int(value, f"[{region}] {ctx}.{key}") for key, value in raw.items()}


def _as_str(value: Any, ctx: str) -> str:
    if not isinstance(value, str):
        raise UnknownRegionError(f"{ctx} : chaîne attendue, obtenu {value!r}")
    return value


def _as_int(value: Any, ctx: str) -> int:
    # bool est une sous-classe d'int : on l'exclut explicitement.
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnknownRegionError(f"{ctx} : entier attendu, obtenu {value!r}")
    return value


def _as_float(value: Any, ctx: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise UnknownRegionError(f"{ctx} : nombre attendu, obtenu {value!r}")
    return float(value)


def _as_opt_int(value: Any, ctx: str) -> int | None:
    if value is None:
        return None
    return _as_int(value, ctx)
