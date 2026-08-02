"""Tests du chargeur de profils de région (regions/loader.py).

TP-41 : le profil factice `zz` se charge sans aucune modification du moteur.
Validation stricte : un profil invalide (seuil hors bornes, bandes qui se
recouvrent, code EPSG non entier) lève UnknownRegionError — jamais un
comportement silencieux (ARCHITECTURE §2, §5).
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from crs_zone_toolkit.core.errors import UnknownRegionError
from crs_zone_toolkit.regions.loader import load_profile


def test_region_inconnue_leve_unknown_region_error(tmp_path: Path) -> None:
    # Répertoire vide : aucun profil `zz` → erreur explicite, pas de None.
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=tmp_path)


def test_charge_le_profil_zz(zz_regions_dir: Path) -> None:
    profile = load_profile("zz", regions_dir=zz_regions_dir)

    assert profile.id == "zz"
    assert profile.seuils.part_dominante_min == 0.75
    assert profile.seuils.n_echantillons == 10
    assert [f.zone for f in profile.fuseaux] == [1, 2]
    assert profile.fuseaux[0].epsg_csrs == 99991


def test_part_dominante_hors_intervalle_invalide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    mauvais = zz_profil_toml.replace("part_dominante_min = 0.75", "part_dominante_min = 1.5")
    regions_dir = make_regions_dir("zz", mauvais)
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=regions_dir)


def test_bandes_qui_se_recouvrent_invalides(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    # Fuseau 2 démarre à 0.5 au lieu de 1.0 → recouvrement avec le fuseau 1.
    mauvais = zz_profil_toml.replace(
        "zone = 2\nmeridien_central = 1.5\nlon_min = 1.0",
        "zone = 2\nmeridien_central = 1.5\nlon_min = 0.5",
    )
    regions_dir = make_regions_dir("zz", mauvais)
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=regions_dir)


def test_code_epsg_non_entier_invalide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    mauvais = zz_profil_toml.replace("epsg_csrs = 99991", 'epsg_csrs = "99991"')
    regions_dir = make_regions_dir("zz", mauvais)
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=regions_dir)


def test_multi_zones_sans_csrs_invalide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    # La section [multi_zones] existe (clé 'nad83') mais ne définit pas 'csrs' :
    # le moteur (measure_crs, _lambert_epsg) suppose sa présence (M4).
    mauvais = zz_profil_toml.replace("csrs = 99999", "nad83 = 88880")
    regions_dir = make_regions_dir("zz", mauvais)
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=regions_dir)


def test_profil_qc_charge_les_crs_reconnus() -> None:
    from crs_zone_toolkit.regions.loader import load_profile

    profile = load_profile("qc")
    par_etiquette = {r.etiquette: r.codes for r in profile.reconnus}
    assert par_etiquette["SCoPQ zone 2"] == (2944,)
    assert par_etiquette["MTQ Lambert"] == (3797, 3798, 3799)
    assert par_etiquette["Québec Albers"] == (6623, 6624)


def test_profil_sans_reconnus_donne_tuple_vide(
    zz_regions_dir: object,
) -> None:
    from crs_zone_toolkit.regions.loader import load_profile

    profile = load_profile("zz", regions_dir=zz_regions_dir)  # type: ignore[arg-type]
    assert profile.reconnus == ()


def test_load_grid_qc_retourne_les_neuf_fuseaux() -> None:
    from crs_zone_toolkit.regions.loader import load_grid, load_profile

    profile = load_profile("qc")
    grille = load_grid(profile)
    assert len(grille) == 9
    assert set(grille["zone"]) == {2, 3, 4, 5, 6, 7, 8, 9, 10}
    assert grille.crs is not None


# ── familles_grille_obligatoire (DT-01) ────────────────────────────────────
# Champ REQUIS : un profil qui l'oublierait perdrait la protection NAD27 sans
# le savoir. Le loader doit donc échouer, pas retenir un défaut permissif.


def test_charge_familles_grille_obligatoire(zz_regions_dir: Path) -> None:
    profile = load_profile("zz", regions_dir=zz_regions_dir)
    assert profile.familles_grille_obligatoire == ("nad27",)


def test_familles_grille_obligatoire_manquante_invalide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    sans = zz_profil_toml.replace('familles_grille_obligatoire = ["nad27"]\n', "")
    regions_dir = make_regions_dir("zz", sans)
    with pytest.raises(UnknownRegionError, match="familles_grille_obligatoire"):
        load_profile("zz", regions_dir=regions_dir)


def test_familles_grille_obligatoire_non_liste_invalide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    mauvais = zz_profil_toml.replace(
        'familles_grille_obligatoire = ["nad27"]', 'familles_grille_obligatoire = "nad27"'
    )
    regions_dir = make_regions_dir("zz", mauvais)
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=regions_dir)


def test_familles_grille_obligatoire_element_non_chaine_invalide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    mauvais = zz_profil_toml.replace(
        'familles_grille_obligatoire = ["nad27"]', "familles_grille_obligatoire = [27]"
    )
    regions_dir = make_regions_dir("zz", mauvais)
    with pytest.raises(UnknownRegionError):
        load_profile("zz", regions_dir=regions_dir)


# ── etiquette_multi_zones (DT-20 n°1) ──────────────────────────────────────
# Champ OPTIONNEL : donnée régionale d'affichage, jamais de valeur par défaut
# permissive côté moteur (le repli sur le nom pyproj vit dans core/analysis.py).


def test_profil_qc_charge_etiquette_multi_zones() -> None:
    profile = load_profile("qc")
    assert profile.etiquette_multi_zones == "Québec Lambert"


def test_profil_sans_etiquette_multi_zones_donne_none(zz_regions_dir: Path) -> None:
    profile = load_profile("zz", regions_dir=zz_regions_dir)
    assert profile.etiquette_multi_zones is None


def test_familles_grille_obligatoire_vide_est_valide(
    make_regions_dir: Callable[[str, str], Path], zz_profil_toml: str
) -> None:
    """Une région sans datum historique déclare [] — explicitement, pas par omission."""
    vide = zz_profil_toml.replace(
        'familles_grille_obligatoire = ["nad27"]', "familles_grille_obligatoire = []"
    )
    regions_dir = make_regions_dir("zz", vide)
    assert load_profile("zz", regions_dir=regions_dir).familles_grille_obligatoire == ()
