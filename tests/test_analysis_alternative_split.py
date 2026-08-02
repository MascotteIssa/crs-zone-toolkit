"""DT-25 — le compte de la ligne « Alternative : découpage » (observation N3).

La ligne annonçait le nombre de fuseaux **traversés**, pas de fichiers
**produits**. L'affectation étant majoritaire (SPEC §5), une entité à cheval ne
va que dans un seul fichier : sur le terrain, `regio_s` annonçait 9 sorties et
en produisait 6 ; `munic_mauricie` annonçait 3 et en produisait **1**. La somme
des entités était conservée dans les deux cas — c'est le compte qui mentait,
pas la donnée.

Ce n'est pas cosmétique : c'est un **chiffre faux affiché avant une décision**.
Quelqu'un qui renonce au découpage en jugeant « 9 fichiers, c'est trop » décide
sur une donnée fausse.

Ces tests confrontent l'annonce à ce qu'`apply` produit **réellement** — la
seule façon de garantir qu'ils ne dérivent pas l'un de l'autre.
"""

from __future__ import annotations

from crs_zone_toolkit.core.analysis import _fuseau_par_zone, _zone_epsg, analyze
from crs_zone_toolkit.core.apply import apply
from crs_zone_toolkit.core.results import Decision
from crs_zone_toolkit.core.targets import target_family

# ── DT-25 — le compte annoncé doit être celui des fichiers produits ────────
#
# Observation N3 : la ligne « Alternative : découpage par fuseau (N sorties) »
# annonçait le nombre de fuseaux TRAVERSÉS, pas de fichiers PRODUITS —
# l'affectation étant majoritaire, une entité à cheval ne va que dans un seul
# fichier. Sur le terrain : regio_s annonce 9 → 6 fichiers ; munic_mauricie
# annonce 3 → 1. La somme des entités est conservée dans les deux cas : c'est
# le compte qui ment, pas la donnée. Un chiffre faux AVANT une décision.


def _alt_split(result) -> dict | None:
    return next((a for a in result.recommandation.alternatives if a.get("action") == "split"), None)


def test_dt25_le_compte_annonce_egale_les_fichiers_produits(
    tp02bis_deux_fuseaux_majoritaires, qc_profile, qc_grid, tmp_path
) -> None:
    """Le test que N3 réclame : ce qui est annoncé est ce qui sort.

    Une ligne dont 70 % de la longueur est en fuseau 9 et 30 % en fuseau 8
    traverse DEUX fuseaux mais, par affectation majoritaire, ne produit qu'UN
    fichier.
    """
    layer = tp02bis_deux_fuseaux_majoritaires
    result = analyze(layer, "ligne", profile=qc_profile, grid=qc_grid)
    alt = _alt_split(result)
    assert alt is not None, "deux fuseaux traversés : le découpage est bien offert"

    produit = apply(
        layer,
        "ligne",
        result,
        Decision(choix="split", origine="test"),
        profile=qc_profile,
        grid=qc_grid,
        out_dir=tmp_path,
    )

    assert len(alt["zones"]) == len(produit.fichiers), (
        f"annoncé {len(alt['zones'])} sorties, produit {len(produit.fichiers)} fichiers"
    )


def test_dt25_le_decoupage_reste_offert_quand_il_produit_plusieurs_fichiers(
    tp02bis_deux_fuseaux_majoritaires, qc_profile, qc_grid
) -> None:
    """Contre-épreuve : corriger le COMPTE ne doit pas retirer l'ALTERNATIVE.

    *Reformulée le 2026-08-02 (N20/N23).* Elle disait « le découpage reste offert
    dès **deux fuseaux traversés** » — c'est précisément ce que N20 a invalidé :
    traverser deux fuseaux ne suffit pas, encore faut-il que l'affectation
    majoritaire en peuple deux. La couche de ce fichier a changé pour cette raison.
    """
    result = analyze(tp02bis_deux_fuseaux_majoritaires, "ligne", profile=qc_profile, grid=qc_grid)

    assert len(result.zones_traversees) == 2
    assert _alt_split(result) is not None


def test_dt25_les_zones_annoncees_sont_celles_qui_recevront_des_entites(
    tp02bis_deux_fuseaux_majoritaires, qc_profile, qc_grid, tmp_path
) -> None:
    """Pas seulement le bon nombre : les bons fuseaux."""
    layer = tp02bis_deux_fuseaux_majoritaires
    result = analyze(layer, "ligne", profile=qc_profile, grid=qc_grid)

    produit = apply(
        layer,
        "ligne",
        result,
        Decision(choix="split", origine="test"),
        profile=qc_profile,
        grid=qc_grid,
        out_dir=tmp_path,
    )

    epsg_produits = {f.epsg for f in produit.fichiers}
    epsg_annonces = {
        _zone_epsg(_fuseau_par_zone(qc_profile, z), target_family(result.famille))
        for z in _alt_split(result)["zones"]
    }
    assert epsg_annonces == epsg_produits


def test_dt25_somme_des_entites_conservee(
    tp02bis_deux_fuseaux_majoritaires, qc_profile, qc_grid, tmp_path
) -> None:
    """Garde-fou : aucune entité ne doit disparaître du découpage."""
    layer = tp02bis_deux_fuseaux_majoritaires
    result = analyze(layer, "ligne", profile=qc_profile, grid=qc_grid)
    produit = apply(
        layer,
        "ligne",
        result,
        Decision(choix="split", origine="test"),
        profile=qc_profile,
        grid=qc_grid,
        out_dir=tmp_path,
    )
    assert sum(f.n_entites for f in produit.fichiers) == len(layer)


def test_dt25_le_menu_et_la_ligne_alternative_annoncent_le_meme_compte(
    tp02bis_deux_fuseaux_majoritaires, qc_profile, qc_grid
) -> None:
    """Second site manqué à la clôture de DT-25 — et le pire des deux.

    `apply_menu` ligne `[3]` comptait encore les fuseaux **traversés**. Sur
    `regio_s`, le même écran de décision aurait annoncé « 6 sorties » à la ligne
    Alternative et « 9 sorties » au menu : une contradiction interne, sur
    l'écran même où l'utilisateur choisit.
    """
    from crs_zone_toolkit.core import messages as msg

    result = analyze(tp02bis_deux_fuseaux_majoritaires, "ligne", profile=qc_profile, grid=qc_grid)
    attendu = len(_alt_split(result)["zones"])

    ligne_menu = next(ligne for ligne in msg.apply_menu(result) if ligne.startswith("  [3]"))

    assert f"{attendu} sortie" in ligne_menu
    assert attendu >= 2, "prémisse : le découpage doit vraiment produire plusieurs fichiers"
