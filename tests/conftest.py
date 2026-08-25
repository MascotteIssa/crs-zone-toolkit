"""Fixtures pytest — TOUS les jeux de test sont générés ici par code (TEST_PLAN, principe 1).

Aucun fichier géospatial binaire committé. Chaque fixture porte l'ID du cas
qu'elle sert (TP-xx) et construit ses géométries aux coordonnées choisies
exprès pour la règle testée (repères : TEST_PLAN, principe 3). Le profil
factice `zz` (TP-41) se construit ici aussi, dans un tmp_path.
"""

from collections.abc import Callable
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box

# ── Tests qui exigent un dépôt git ─────────────────────────────────────────
# Quelques tests interrogent l'ARBRE DU DÉPÔT (`git ls-files`, `git status`) ou
# supposent un état complet : périmètre de publication, balayage des documents
# publiés, existence des cibles de lien du README. Ils n'ont pas de sens depuis
# un sdist déplié, qui n'est pas un dépôt git et ne porte qu'un EXTRAIT de
# l'arbre (`docs/images/` par exemple en est exclu, cf. `pyproject.toml`).
#
# Sans cette garde ils ne sautaient pas : ils ÉCHOUAIENT (`git` en code 128),
# ce qui rendait fausse la promesse de DT-21 — « la suite se rejoue depuis
# l'archive dépliée ». Constaté le 2026-08-25 sur le sdist 0.2.0 et reproduit
# sur le sdist **0.1.0 publié**, donc antérieur à cette passe. La propriété
# elle-même n'a toujours aucune garde automatique : DT-32.
#
# Marqueur plutôt qu'objet importé : `tests/` n'a pas d'`__init__.py`, donc un
# `from .conftest import …` ne résout pas. Le conftest étant chargé d'office
# par pytest, le marqueur est disponible partout sans import ni duplication.
RACINE_DEPOT = Path(__file__).resolve().parent.parent
DANS_UN_DEPOT_GIT = (RACINE_DEPOT / ".git").exists()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requiert_depot_git: test qui interroge l'arbre du dépôt — sauté hors dépôt git",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if DANS_UN_DEPOT_GIT:
        return
    saut = pytest.mark.skip(
        reason="exige l'arbre du dépôt git (sdist déplié) — cf. conftest, DT-21"
    )
    for item in items:
        if item.get_closest_marker("requiert_depot_git") is not None:
            item.add_marker(saut)


# ── Profil factice `zz` (TP-41) ────────────────────────────────────────────
# Deux fuseaux fictifs, bandes contiguës (0–1, 1–2), seuils exotiques : la
# preuve qu'une nouvelle région = un dossier de plus, sans toucher au moteur.
ZZ_PROFIL_TOML = """\
[profil]
id = "zz"
nom = "Zone fictive"
version = "0.0"
grille = "grille_zz.geojson"
limite = "limite_zz.geojson"

[seuils]
part_dominante_min = 0.75
distorsion_max_ppm = 999
n_echantillons = 10

[datum]
famille_defaut = "csrs"
familles_grille_obligatoire = ["nad27"]
[datum.geographiques]
csrs = 4617
wgs84 = 4326

[multi_zones]
csrs = 99999

[[fuseaux]]
zone = 1
meridien_central = 0.5
lon_min = 0.0
lon_max = 1.0
epsg_csrs = 99991
epsg_nad83 = 88881

[[fuseaux]]
zone = 2
meridien_central = 1.5
lon_min = 1.0
lon_max = 2.0
epsg_csrs = 99992
epsg_nad83 = 88882
"""


@pytest.fixture
def make_regions_dir(tmp_path: Path) -> Callable[[str, str], Path]:
    """Fabrique un répertoire de profils contenant <region>/profil.toml.

    Retourne le répertoire racine à passer à load_profile(..., regions_dir=).
    """

    def _make(region: str, toml_text: str) -> Path:
        profil = tmp_path / region / "profil.toml"
        profil.parent.mkdir(parents=True, exist_ok=True)
        profil.write_text(toml_text, encoding="utf-8")
        return tmp_path

    return _make


@pytest.fixture
def zz_profil_toml() -> str:
    """Texte TOML du profil `zz` valide — à muter pour les cas invalides."""
    return ZZ_PROFIL_TOML


@pytest.fixture
def zz_regions_dir(make_regions_dir: Callable[[str, str], Path]) -> Path:
    """Répertoire de profils contenant le profil factice `zz` valide (TP-41)."""
    return make_regions_dir("zz", ZZ_PROFIL_TOML)


@pytest.fixture
def zz_boundary() -> gpd.GeoDataFrame:
    """Emprise fictive couvrant les deux bandes zz (lon 0–2), lat 10–12 (EPSG:4326)."""
    return gpd.GeoDataFrame(geometry=[box(0.0, 10.0, 2.0, 12.0)], crs=4326)


@pytest.fixture
def zz_boundary_etroit() -> gpd.GeoDataFrame:
    """Emprise fictive plus étroite que les bandes zz — la découpe doit les réduire."""
    return gpd.GeoDataFrame(geometry=[box(0.3, 10.5, 1.7, 11.5)], crs=4326)


# ── Profil qc réel + grille committée (TP-01 et suivants) ──────────────────


@pytest.fixture(scope="session")
def qc_profile():
    from crs_zone_toolkit.regions.loader import load_profile

    return load_profile("qc")


@pytest.fixture(scope="session")
def qc_grid(qc_profile):
    from crs_zone_toolkit.regions.loader import load_grid

    return load_grid(qc_profile)


def _points(coords: list[tuple[float, float]], crs: int = 4326) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in coords], crs=crs)


@pytest.fixture
def tp01_points_fuseau7() -> gpd.GeoDataFrame:
    """50 points dans bbox 72°O–71,5°O × 45,3–45,6°N (fuseau 7), EPSG:4326."""
    rng = np.random.default_rng(7)
    lons = rng.uniform(-72.0, -71.5, 50)
    lats = rng.uniform(45.3, 45.6, 50)
    return _points(list(zip(lons.tolist(), lats.tolist(), strict=True)))


@pytest.fixture
def tp02_lignes_deux_fuseaux() -> gpd.GeoDataFrame:
    """Lignes est-ouest traversant 75°O (frontière fuseaux 8/9), ~58 % côté fuseau 9.

    Fuseau 9 = lon [-78,-75], fuseau 8 = lon [-75,-72]. Chaque ligne va de
    -76,16 (côté 9, longueur 1,16) à -74,16 (côté 8, longueur 0,84) → 58/42.
    """
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    return gpd.GeoDataFrame(geometry=lignes, crs=4326)


@pytest.fixture
def tp03_polygones_quatre_fuseaux() -> gpd.GeoDataFrame:
    """Bande est-ouest 78,5°O → 70°O couvrant les fuseaux 7-8-9-10, lat 46,8–47,2."""
    from shapely.geometry import box as _box

    return gpd.GeoDataFrame(geometry=[_box(-78.5, 46.8, -70.0, 47.2)], crs=4326)


@pytest.fixture
def hors_profil_total_points() -> gpd.GeoDataFrame:
    """5 points à Winnipeg (Manitoba) : hors de tout fuseau MTM et hors profil québécois."""
    return _points([(-97.15 + i * 0.01, 49.90 + i * 0.01) for i in range(5)])


@pytest.fixture
def tp04_dominant_fuseau8_distorsion_ok() -> gpd.GeoDataFrame:
    """95 % des points dans le fuseau 8 (près du MC -73,5), 5 % juste au-delà de 75°O."""
    rng = np.random.default_rng(8)
    lons = rng.uniform(-74.5, -72.5, 95).tolist() + rng.uniform(-75.4, -75.05, 5).tolist()
    lats = rng.uniform(46.0, 46.5, 100).tolist()
    return _points(list(zip(lons, lats, strict=True)))


@pytest.fixture
def tp05_dominant_fuseau8_distorsion_ko() -> gpd.GeoDataFrame:
    """91 % dans le fuseau 8, 9 % très à l'ouest (≥77,5°O) → max ppm au-delà du seuil."""
    rng = np.random.default_rng(5)
    lons = rng.uniform(-74.8, -72.2, 91).tolist() + rng.uniform(-78.0, -77.5, 9).tolist()
    lats = rng.uniform(46.0, 46.5, 100).tolist()
    return _points(list(zip(lons, lats, strict=True)))


@pytest.fixture
def tp07_lignes_nad83_origine(tp02_lignes_deux_fuseaux) -> gpd.GeoDataFrame:
    """TP-02 réécrit en EPSG:4269 (NAD83 d'origine)."""
    return tp02_lignes_deux_fuseaux.set_crs(4269, allow_override=True)


@pytest.fixture
def tp08_points_nad27_fuseau4() -> gpd.GeoDataFrame:
    """Points du fuseau 4 déclarés en EPSG:32084 (NAD27 / MTM zone 4)."""
    # Coordonnées projetées plausibles près du MC -61,5 : on part de lon/lat puis on projette.
    pts = _points([(-61.6, 48.0), (-61.4, 48.1), (-61.5, 48.2), (-61.55, 47.9)])
    return pts.to_crs(32084)


@pytest.fixture
def tp09_points_scopq_zone2() -> gpd.GeoDataFrame:
    """Points de l'est du Québec déclarés en EPSG:2944 (SCoPQ zone 2)."""
    pts = _points([(-55.5, 50.0), (-55.6, 50.1), (-55.4, 49.9)])
    return pts.to_crs(2944)


@pytest.fixture
def tp10_points_mtq_lambert() -> gpd.GeoDataFrame:
    """Points déclarés en EPSG:3798 (MTQ Lambert NAD83)."""
    pts = _points([(-71.0, 46.8), (-73.0, 46.5), (-70.5, 47.0)])
    return pts.to_crs(3798)


@pytest.fixture
def tp06_sans_crs() -> gpd.GeoDataFrame:
    """Points du fuseau 8 SANS CRS déclaré (simule un .prj supprimé)."""
    gdf = _points([(-73.5, 46.0), (-73.4, 46.1), (-73.6, 46.2)])
    return gdf.set_crs(None, allow_override=True)


@pytest.fixture
def multipoint_layer() -> gpd.GeoDataFrame:
    """Couche MultiPoint (fuseau 8, près du MC -73,5), EPSG:4326.

    `_sample_lonlat` doit rester robuste face à un type de géométrie qui n'a
    ni `.x` ni `.y` (I1 — fix clôture revue J2).
    """
    multipoints = [
        MultiPoint([(-73.6, 46.0), (-73.4, 46.1)]),
        MultiPoint([(-73.5, 46.05), (-73.55, 46.15), (-73.45, 45.95)]),
    ]
    return gpd.GeoDataFrame(geometry=multipoints, crs=4326)


@pytest.fixture
def tp13_polygone_papillon() -> gpd.GeoDataFrame:
    """Polygone auto-intersectant (papillon) réparable par make_valid, dans le fuseau 8."""
    papillon = Polygon([(-73.6, 46.0), (-73.4, 46.2), (-73.4, 46.0), (-73.6, 46.2), (-73.6, 46.0)])
    return gpd.GeoDataFrame(geometry=[papillon], crs=4326)


@pytest.fixture
def couche_geometrie_irreparable() -> gpd.GeoDataFrame:
    """Papillon (invalide) + polygone déjà vide : make_valid ne peut pas rendre le
    lot entièrement valide-et-non-vide (M3 — branche `InvalidGeometryError`).

    Le polygone vide est déjà valide (`is_valid`), donc `make_valid` le laisse
    inchangé (toujours vide) : après réparation, `is_empty.any()` reste vrai.
    """
    papillon = Polygon([(-73.6, 46.0), (-73.4, 46.2), (-73.4, 46.0), (-73.6, 46.2), (-73.6, 46.0)])
    vide = Polygon()
    return gpd.GeoDataFrame(geometry=[papillon, vide], crs=4326)


@pytest.fixture
def tp22_croissant_a_cheval() -> gpd.GeoDataFrame:
    """Polygone en croissant à cheval sur 75°O : surface majoritaire fuseau 8,
    centroïde côté fuseau 9. Fuseau 8 = lon [-75,-72], fuseau 9 = lon [-78,-75].

    Calage vérifié numériquement contre la grille qc committée, reprojetée en
    EPSG:6622 (Québec Lambert, `multi_zones.csrs`) : le gros lobe est-de -75
    (quadrilatère) porte l'essentiel de la surface en fuseau 8 (~20,28 milliards
    de m² d'intersection avec la cellule fuseau 8) ; la fine pointe ouest, tirée
    jusqu'à -80,0°, porte moins de surface en fuseau 9 (~15,78 milliards de m²,
    ratio 8/9 ≈ 1,28) mais suffit à déplacer le centroïde géographique (EPSG:4326)
    à x ≈ -75,127, côté fuseau 9. Preuve que l'affectation par majorité surfacique
    (moteur, Task 6) diffère bien d'une affectation par centroïde.
    """
    from shapely.geometry import Polygon as _P

    # gros lobe à l'est de -75 (fuseau 8), fine pointe tirée loin à l'ouest (fuseau 9)
    poly = _P(
        [
            (-74.9, 46.0),
            (-72.5, 45.7),
            (-72.3, 46.6),
            (-74.9, 46.9),
            (-80.0, 46.45),
        ]
    )
    return gpd.GeoDataFrame(geometry=[poly], crs=4326)


@pytest.fixture
def tp23_ligne_majorite_fuseau9() -> gpd.GeoDataFrame:
    """Ligne dont 70 % de la longueur est en fuseau 9 (lon [-78,-75]).

    De -76,4 (fuseau 9) à -74,4 (fuseau 8) : 1,4° en fuseau 9 contre 0,6° en
    fuseau 8 (vérifié : 1,4 / (1,4 + 0,6) = 0,70).
    """
    from shapely.geometry import LineString as _L

    return gpd.GeoDataFrame(geometry=[_L([(-76.4, 46.0), (-74.4, 46.0)])], crs=4326)


@pytest.fixture
def tp11_points_partiellement_hors() -> gpd.GeoDataFrame:
    """85 % fuseau 9 (Québec), 15 % côté Ontario au-delà de la limite découpée."""
    rng = np.random.default_rng(11)
    quebec = list(
        zip(
            rng.uniform(-77.2, -75.6, 85).tolist(),
            rng.uniform(46.1, 47.0, 85).tolist(),
            strict=True,
        )
    )
    ontario = list(
        zip(
            rng.uniform(-81.0, -80.0, 15).tolist(),
            rng.uniform(43.0, 44.0, 15).tolist(),
            strict=True,
        )
    )
    return _points(quebec + ontario)


@pytest.fixture
def tp02bis_deux_fuseaux_majoritaires() -> gpd.GeoDataFrame:
    """Deux fuseaux **majoritaires** — le cas où le découpage produit vraiment 2 fichiers.

    À distinguer de `tp02_lignes_deux_fuseaux`, dont les trois lignes sont toutes à
    cheval et donc toutes majoritaires dans le fuseau 9 : là, le découpage ne rendrait
    qu'un fichier et n'est plus offert (observations N20/N23, SPEC §4.3 amendé).

    Proportions calées sur la maquette `CLI_UX` §3 (58 % / 42 %) : une ligne de 1,4°
    entièrement en fuseau 9 (lon [-78,-75]), une de 1,0° entièrement en fuseau 8
    (lon [-75,-72]) — 1,4 / 2,4 = 0,583. Latitude 47,5° : entièrement en territoire
    québécois, donc `part_hors_profil` nul, et parts mesurées **58,3 % / 41,7 %** —
    les chiffres mêmes de la maquette.
    """
    from shapely.geometry import LineString as _L

    return gpd.GeoDataFrame(
        geometry=[
            _L([(-77.4, 47.5), (-76.0, 47.5)]),  # fuseau 9
            _L([(-74.0, 47.5), (-73.0, 47.5)]),  # fuseau 8
        ],
        crs=4326,
    )
