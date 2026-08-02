"""DT-29 — passe de restitution du résumé terminal (N18, N2, N2 bis, N1, N7).

Cinq défauts sans rapport entre eux sauf leur nature : aucun ne touche au
moteur, tous touchent ce que l'utilisateur **voit**. Ils sont testés ici comme
des **fonctions pures** — jamais par assertion sur un rendu terminal, que
TEST_PLAN §5 réserve aux tests dorés des écrans de `CLI_UX.md`.

Le placement de l'enveloppement dans `messages.py` suit le précédent assumé de
`analyse_bloc_fuseaux` (« mise en page dans messages vs affichage ») : la mise
en forme du texte français y vit déjà, et cela la rend testable sans passer
par une console.
"""

from __future__ import annotations

import pytest

from crs_zone_toolkit.core import messages as msg

# ── N18 — enveloppement avec retrait de continuation ──────────────────────


def test_n18_les_lignes_suivantes_s_alignent_sous_le_texte() -> None:
    """Le défaut : toute ligne qui déborde reprenait en **colonne 0**.

    Résultat à l'écran — « Note : NAD83(CSRS) est le standard actuel. » venait
    se coller à la marge gauche, sous un `⚠` indenté, cassant la structure.
    """
    texte = "Le fuseau MTM 8 est la projection unique la moins déformée, mais dépasse la tolérance."
    lignes = msg.envelopper(texte, largeur=50, tete="  ")

    assert len(lignes) > 1, "prémisse : le texte doit bel et bien déborder"
    assert lignes[0].startswith("  ") and not lignes[0].startswith("   ")
    for suite in lignes[1:]:
        assert suite.startswith("  "), "les suites reprenaient en colonne 0"
        assert suite[2] != " ", "alignées SOUS le texte, pas au-delà"


def test_n18_le_retrait_suit_la_largeur_du_prefixe() -> None:
    """Une ligne à glyphe (`  ⚠ …`) aligne ses suites sous le texte, pas sous le glyphe."""
    texte = "Entrée en NAD83 d'origine : la famille est préservée sans changement silencieux."
    lignes = msg.envelopper(texte, largeur=46, tete="  ⚠ ")

    assert lignes[0].startswith("  ⚠ ")
    assert len(lignes) > 1
    for suite in lignes[1:]:
        assert suite.startswith("    ") and suite[4] != " "


@pytest.mark.parametrize("largeur", [40, 60, 99, 100])
def test_n18_aucune_ligne_ne_depasse_la_largeur(largeur: int) -> None:
    texte = " ".join(["mot"] * 60)
    for ligne in msg.envelopper(texte, largeur=largeur, tete="  ⚠ "):
        assert len(ligne) <= largeur


def test_n18_un_chemin_sans_espace_reste_entier() -> None:
    """Un chemin coupé en deux n'est plus copiable : mieux vaut le laisser déborder."""
    chemin = "C:/un/tres/long/chemin/sans/aucune/espace/pour/couper/sortie_epsg2950.gpkg"
    lignes = msg.envelopper(f"Sortie : {chemin} (EPSG:2950)", largeur=40, tete="")

    assert any(chemin in ligne for ligne in lignes), "le chemin ne doit pas être scindé"


def test_n18_un_texte_court_reste_une_seule_ligne() -> None:
    assert msg.envelopper("Motif : court.", largeur=99, tete="  ") == ["  Motif : court."]


# ── N1 — accord singulier/pluriel ─────────────────────────────────────────


def test_n1_une_seule_entite_s_ecrit_au_singulier() -> None:
    """« 1 entités » sur la PREMIÈRE ligne de toute analyse mono-entité, en français."""
    assert "1 entité," in msg.analyse_ligne_couche("montreal.gpkg", "polygon", 1)


@pytest.mark.parametrize("n", [0, 2, 21, 12580])
def test_n1_les_autres_effectifs_restent_au_pluriel(n: int) -> None:
    """0 et 2+ prennent le pluriel — en français, seul 1 est singulier."""
    assert " entités," in msg.analyse_ligne_couche("x.gpkg", "polygon", n)


def test_n1_une_seule_sortie_s_ecrit_au_singulier() -> None:
    """Second site, révélé par DT-25 : le compte peut désormais valoir 1."""
    assert "1 sortie," in msg.analyse_ligne_alternative_split(1)
    assert "6 sorties," in msg.analyse_ligne_alternative_split(6)


# ── N7 — le zéro négatif ──────────────────────────────────────────────────


def test_n7_un_arrondi_a_zero_ne_porte_pas_de_signe_moins() -> None:
    """`−0 ppm` : le signe était choisi sur la valeur brute, l'arrondi l'effaçait ensuite."""
    assert msg._ppm_affiche(-0.4) == "0 ppm"
    assert msg._ppm_affiche(0.4) == "0 ppm"
    assert msg._ppm_affiche(0.0) == "0 ppm"


def test_n7_les_valeurs_significatives_gardent_leur_signe() -> None:
    """Contre-épreuve : tester le signe après arrondi ne doit rien effacer d'autre."""
    assert msg._ppm_affiche(-100.0) == "−100 ppm"
    assert msg._ppm_affiche(41.4) == "+41 ppm"
    assert msg._ppm_affiche(-0.6) == "−1 ppm"


# ── N2 bis — une ligne vide avant le menu de décision ─────────────────────


def test_n2bis_le_menu_commence_par_une_ligne_vide() -> None:
    """Le résumé et le menu se touchaient, sur un écran de **décision**."""
    from crs_zone_toolkit.core.results import (
        AnalysisResult,
        Emprise,
        Recommandation,
        ZonePart,
    )

    result = AnalysisResult(
        schema_version=1,
        couche="x",
        crs_entree={"epsg": 4326, "etiquette": "WGS 84", "suppose": False, "reconnu": None},
        famille="wgs84",
        type_geometrie="line",
        emprise=Emprise(-76.0, 46.0, -74.0, 46.5),
        zones_traversees=(
            ZonePart(zone=8, epsg=2950, part=0.6),
            ZonePart(zone=9, epsg=2951, part=0.4),
        ),
        part_hors_profil=0.0,
        distorsions=(),
        recommandation=Recommandation(
            "zone",
            2950,
            "MTM fuseau 8",
            "zone_dominante",
            "motif",
            ({"action": "split", "zones": [8, 9]},),
        ),
        avertissements=(),
        parametres={},
    )

    lignes = msg.apply_menu(result)

    assert lignes[0] == "", "aucune respiration ne séparait le résumé du menu"
    assert lignes[1].startswith("Que voulez-vous faire ?")


# ── Câblage : l'invariant, pas le libellé ─────────────────────────────────
#
# Les tests ci-dessus portent sur des fonctions pures ; ils passeraient tous
# même si `affichage` n'appelait jamais `envelopper`. La garde qui suit vérifie
# la PROPRIÉTÉ que N18 nomme — « aucune ligne ne déborde » — sans asserter le
# moindre libellé : elle ne double donc pas les tests dorés (TEST_PLAN §5/§7).


def _lignes_rendues(largeur: int) -> list[str]:
    import io
    from pathlib import Path

    import geopandas as gpd
    from rich.console import Console
    from shapely.geometry import LineString

    from crs_zone_toolkit import affichage
    from crs_zone_toolkit.core.analysis import analyze
    from crs_zone_toolkit.core.targets import target_family
    from crs_zone_toolkit.regions.loader import load_grid, load_profile

    profile = load_profile("qc")
    grid = load_grid(profile)
    # Deux fuseaux MAJORITAIRES : motif long, et la ligne « Alternative » présente —
    # sans elle, la garde de câblage ci-dessous ne couvrirait pas cette ligne
    # (couche changée le 2026-08-02, cf. N20/N23).
    couche = gpd.GeoDataFrame(
        geometry=[
            LineString([(-77.4, 47.5), (-76.0, 47.5)]),
            LineString([(-74.0, 47.5), (-73.0, 47.5)]),
        ],
        crs=4326,
    )
    result = analyze(couche, "routes", profile=profile, grid=grid)
    tampon = io.StringIO()
    affichage.resume_analyse(
        Console(file=tampon, width=largeur, no_color=True, legacy_windows=False),
        result,
        Path("routes_analyse_crs_20260801-120000.html"),
        couche=Path("routes.geojson"),
        n_entites=len(couche),
        profile=profile,
        crs_geographique=True,
        famille_cible=target_family(result.famille),
    )
    return tampon.getvalue().splitlines()


@pytest.mark.parametrize("largeur", [70, 99, 100])
def test_n18_aucune_ligne_du_resume_ne_deborde(largeur: int) -> None:
    """Propriété, pas libellé : le résumé tient dans la largeur qu'on lui donne.

    C'est le symptôme visible de N18 — une ligne qui déborde est une ligne que
    le terminal renverra en colonne 0.
    """
    trop_longues = [ligne for ligne in _lignes_rendues(largeur) if len(ligne.rstrip()) > largeur]
    assert trop_longues == []


def test_n18_le_resume_passe_bien_par_l_enveloppement(monkeypatch) -> None:
    """Le câblage : sans cet espion, `envelopper` pouvait n'être appelée par personne.

    La propriété de largeur ci-dessus ne suffit pas — Rich tronquait déjà à la
    largeur, en renvoyant simplement la suite en colonne 0. C'est la conjonction
    des deux qui prouve le retrait de continuation : les tests de fonction pure
    montrent que `envelopper` aligne, celui-ci montre qu'elle est employée.
    """
    appels: list[str] = []
    vrai = msg.envelopper

    def espion(texte: str, largeur: int, tete: str) -> list[str]:
        appels.append(tete)
        return vrai(texte, largeur, tete)

    monkeypatch.setattr(msg, "envelopper", espion)
    _lignes_rendues(99)

    # Compte EXACT : un seuil lâche laisserait retirer un appel sans rien casser
    # (constaté — la garde ne mordait pas). Si une ligne de prose est ajoutée au
    # résumé, ce test doit échouer : c'est le rappel qu'elle passe par l'enveloppement.
    assert appels == ["", "", "→ ", "  ", "    ", "  ", "✓ ", "  "], (
        "chaque ligne de prose du résumé doit passer par `envelopper`, avec sa tête"
    )


def test_n2_apply_ne_propose_plus_la_commande_en_cours(tmp_path, monkeypatch) -> None:
    """N2 : `Pour appliquer : crszone apply <couche>` s'affichait DANS `apply`.

    Espion sur le constructeur, sans assertion de texte : sans cette garde, le
    drapeau `suggerer_apply` pouvait exister sans que personne ne le passe.
    """
    import geopandas as gpd
    from shapely.geometry import LineString
    from typer.testing import CliRunner

    from crs_zone_toolkit.cli import app

    src = tmp_path / "routes.geojson"
    gpd.GeoDataFrame(
        geometry=[LineString([(-76.16, y), (-74.16, y)]) for y in (46.0, 46.2)], crs=4326
    ).to_file(src, driver="GeoJSON")

    appels: list[str] = []
    monkeypatch.setattr(msg, "analyse_pour_appliquer", lambda nom: appels.append(nom) or "…")

    res = CliRunner().invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path / "s")])

    assert res.exit_code == 0
    assert appels == []


def test_n2_analyze_la_propose_toujours(tmp_path, monkeypatch) -> None:
    """Contre-épreuve : la ligne s'adresse au lecteur d'une **analyse**, elle y reste."""
    import geopandas as gpd
    from shapely.geometry import LineString
    from typer.testing import CliRunner

    from crs_zone_toolkit.cli import app

    src = tmp_path / "routes.geojson"
    gpd.GeoDataFrame(
        geometry=[LineString([(-76.16, y), (-74.16, y)]) for y in (46.0, 46.2)], crs=4326
    ).to_file(src, driver="GeoJSON")

    appels: list[str] = []
    monkeypatch.setattr(msg, "analyse_pour_appliquer", lambda nom: appels.append(nom) or "…")

    res = CliRunner().invoke(app, ["analyze", str(src), "--report", str(tmp_path / "r")])

    assert res.exit_code == 0
    assert appels == ["routes.geojson"]


# ── N1, sites trouvés en régénérant les démonstrations (DT-17) ────────────
#
# Le bloc `apply --auto` du README, une fois refabriqué depuis le moteur réel,
# affichait « (EPSG:32188, 1 entités) ». Deux sites de plus, invisibles à la
# lecture du code parce qu'ils ne sortent qu'avec une couche mono-entité.


def test_n1_la_ligne_de_sortie_accorde_son_effectif() -> None:
    assert "1 entité)" in msg.apply_ligne_sortie("s/x.gpkg", 32188, 1)
    assert "21 entités)" in msg.apply_ligne_sortie("s/x.gpkg", 32188, 21)


def test_n1_la_grille_accorde_son_effectif() -> None:
    assert "1 entité," in msg.grille_ligne_ecrite("g.geojson", 1, ("zone",))
    assert "9 entités," in msg.grille_ligne_ecrite("g.geojson", 9, ("zone",))
