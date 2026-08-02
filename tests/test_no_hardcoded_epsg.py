"""TP-40 — aucun fait géodésique québécois en dur dans le moteur.

Balaie src/crs_zone_toolkit/core/ et échoue si un code EPSG québécois apparaît
en littéral numérique dans le code (ARCHITECTURE §3, loi 3 ; feuille de route
§1.1). Ces codes ne doivent vivre que dans regions/qc/profil.toml : le noyau
reçoit un RegionProfile, il ne connaît aucune valeur régionale.

On tokenise le source : un code cité dans un commentaire ou une docstring reste
permis (seuls les littéraux de code comptent).
"""

import tokenize
from pathlib import Path

import crs_zone_toolkit

CORE_DIR = Path(crs_zone_toolkit.__file__).resolve().parent / "core"

# Codes EPSG spécifiquement québécois (MTM 2–10, Québec Lambert/Albers,
# MTQ Lambert, SCoPQ) dans les trois familles — DATA_REFERENCE §2 et §4.
# Les codes géographiques globaux (4326/4617/4269/4267) sont volontairement
# exclus : ils ne sont pas spécifiques au Québec.
CODES_INTERDITS = frozenset(
    {
        26899,
        2944,
        2945,
        2946,
        2947,
        2948,
        2949,
        2950,
        2951,
        2952,  # MTM CSRS
        32182,
        32183,
        32184,
        32185,
        32186,
        32187,
        32188,
        32189,
        32190,  # MTM NAD83
        32082,
        32083,
        32084,
        32085,
        32086,  # MTM NAD27
        6622,
        32198,
        32098,  # Québec Lambert
        6623,
        6624,  # Québec Albers
        3797,
        3798,
        3799,  # MTQ Lambert
    }
)


def _literaux_numeriques(chemin: Path) -> list[tuple[int, int]]:
    """Retourne (valeur_entiere, ligne) pour chaque littéral numérique de code."""
    trouves: list[tuple[int, int]] = []
    with chemin.open("rb") as handle:
        for jeton in tokenize.tokenize(handle.readline):
            if jeton.type != tokenize.NUMBER:
                continue
            try:
                valeur = int(jeton.string)
            except ValueError:
                continue  # flottants, hex, etc. — pas un code EPSG
            trouves.append((valeur, jeton.start[0]))
    return trouves


def test_aucun_code_epsg_quebecois_en_dur_dans_core() -> None:
    fautes: list[str] = []
    for module in sorted(CORE_DIR.rglob("*.py")):
        for valeur, ligne in _literaux_numeriques(module):
            if valeur in CODES_INTERDITS:
                fautes.append(f"{module.name}:{ligne} → EPSG {valeur}")
    assert not fautes, (
        "Codes EPSG québécois en dur dans core/ (doivent venir du profil) : " + ", ".join(fautes)
    )
