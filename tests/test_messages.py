"""messages.py : présence et forme des chaînes utilisées par le moteur (J2)."""

import pytest

from crs_zone_toolkit.core import messages as msg


def test_constantes_non_vides() -> None:
    for texte in (
        msg.COUCHE_VIDE,
        msg.CRS_SUPPOSE,
        msg.MAKE_VALID_APPLIQUE,
        msg.GEOM_IRREPARABLE,
        msg.NAD27_NTV2,
        msg.CSRS_STANDARD_ACTUEL,
    ):
        assert isinstance(texte, str) and texte.strip()


def test_gabarits_inserent_les_valeurs() -> None:
    assert "15" in msg.hors_profil(0.153)
    assert "MTQ Lambert" in msg.note_reconnu("MTQ Lambert")
    assert "7" in msg.libelle_fuseau(7)
    assert "8" in msg.motif_zone_moins_deformee(8, 470.0, 200.0, decoupage_utile=True)
    assert "8" in msg.motif_lambert_moins_deforme(8, 470.0, 300.0, decoupage_utile=True)


def test_messages_apply() -> None:
    assert isinstance(msg.AVERTISSEMENT_SHP, str) and msg.AVERTISSEMENT_SHP.strip()
    assert "out.gpkg" in msg.fichier_existant("out.gpkg")
    assert isinstance(msg.NOTE_CHOIX_HORS_RECO, str) and msg.NOTE_CHOIX_HORS_RECO.strip()
    texte = msg.grille_absente(("ca_nrc_NA27SCRS.tif",), "NAD27", "NAD83(CSRS)")
    assert "ca_nrc_NA27SCRS.tif" in texte
    assert "NAD27" in texte and "NAD83(CSRS)" in texte
    assert "(grille non identifiée)" in msg.grille_absente((), "NAD27", "NAD83(CSRS)")


def test_fr_nombre_milliers_et_virgule() -> None:
    """DT-05 : point de vérité unique du format numérique français."""
    assert msg.fr_nombre(1842.5) == "1 842,5"
    assert msg.fr_nombre(12580, dec=0) == "12 580"
    assert msg.fr_nombre(-99.94, dec=1) == "-99,9"


def test_bloc_distorsion_aligne_et_marque_le_hors_seuil() -> None:
    """CLI_UX §2/§3 : en-tête de colonnes, alignement, signe moins Unicode, marqueur hors seuil."""
    from crs_zone_toolkit.core.results import Distorsion

    d = [
        Distorsion(libelle="MTM fuseau 9", epsg=32189, min_ppm=-100, moy_ppm=96, max_ppm=471),
        Distorsion(libelle="Québec Lambert", epsg=32198, min_ppm=38, moy_ppm=102, max_ppm=169),
    ]
    lignes = msg.analyse_bloc_distorsion(d, seuil_ppm=200)

    assert lignes[0].startswith("  Candidat")
    assert lignes[0].rstrip().endswith("max")

    # Alignement : toutes les colonnes ayant une largeur fixe et les valeurs étant
    # cadrées à droite, les lignes de données ont exactement la même longueur une
    # fois le marqueur retiré — et l'en-tête se termine sur la même colonne.
    corps = [ligne.split("  ⚠")[0] for ligne in lignes[1:]]
    assert len({len(ligne) for ligne in corps}) == 1, "colonnes de données non alignées"
    assert len(lignes[0]) == len(corps[0]), "en-tête désaligné des données"

    assert "⚠ hors seuil" in lignes[1]  # 471 ppm > 200
    assert "⚠ hors seuil" not in lignes[2]  # 169 ppm ≤ 200
    assert "−100 ppm" in lignes[1]  # U+2212, pas le trait d'union ASCII
    assert "-100" not in lignes[1]


def test_bloc_distorsion_reste_aligne_avec_une_valeur_extreme() -> None:
    """Régression : une largeur ppm figée à 9 casse l'alignement dès qu'une valeur mesurée
    la dépasse — constaté sur données réelles (couche RTSS, +15793 ppm, 2026-07-28). La
    colonne ppm doit se dimensionner sur le contenu réel comme les deux autres colonnes,
    avec un plancher à 9 (largeur de la maquette CLI_UX §2/§3)."""
    from crs_zone_toolkit.core.results import Distorsion

    d = [
        Distorsion(libelle="MTM fuseau 8", epsg=2950, min_ppm=-100, moy_ppm=460, max_ppm=15793),
        Distorsion(libelle="Québec Lambert", epsg=6622, min_ppm=-7151, moy_ppm=-790, max_ppm=2153),
    ]
    lignes = msg.analyse_bloc_distorsion(d, seuil_ppm=200)

    corps = [ligne.split("  ⚠")[0] for ligne in lignes[1:]]
    assert len({len(ligne) for ligne in corps}) == 1, "colonnes de données non alignées"
    assert len(lignes[0]) == len(corps[0]), "en-tête désaligné des données"
    assert "+15793 ppm" in lignes[1]  # la valeur extrême doit apparaître intacte


def test_recommandation_prefixe_et_famille() -> None:
    """CLI_UX §2 : « reprojeter vers … (EPSG:…, famille) »."""
    ligne = msg.analyse_recommandation("zone", "MTM fuseau 7", 2949, "NAD83(CSRS)")
    assert ligne == "Recommandation : reprojeter vers MTM fuseau 7 (EPSG:2949, NAD83(CSRS))"


def test_recommandation_aucune_ne_montre_jamais_epsg_zero() -> None:
    """100 % hors profil : sentinelle cible_epsg=0 (SPEC §8) — jamais affichée telle quelle."""
    ligne = msg.analyse_recommandation("aucune", "", 0, "NAD83(CSRS)")
    assert "EPSG:0" not in ligne
    assert "aucune" in ligne.lower()


# ── DT-22 — la sentinelle cible_epsg = 0 ne doit fuir dans AUCUNE ligne ────
#
# Le test `test_recommandation_aucune_ne_montre_jamais_epsg_zero` ci-dessus
# gardait la ligne « Recommandation », pas la ligne « Datum » qui la suit — et
# `analyse_ligne_datum` injectait `EPSG:{cible_epsg}` pour `nad83`, `nad27` et
# le repli. Le protocole §5 avait prédit « aucun EPSG:0 » et la prédiction
# était vérifiée : sur la branche `wgs84`, la seule qui n'injecte rien, donc
# la seule qui ne pouvait pas la démentir. D'où le balayage exhaustif ici.

_TOUTES_LES_FAMILLES = ["wgs84", "nad83", "csrs", "nad27", "famille_inconnue"]


@pytest.mark.parametrize("famille", _TOUTES_LES_FAMILLES)
def test_ligne_datum_aucune_ne_montre_jamais_epsg_zero(famille: str) -> None:
    """100 % hors profil : aucune famille ne rend la sentinelle (SPEC §8).

    Balaie **toutes** les familles, y compris le repli : c'est l'angle mort qui
    a laissé passer `Datum : entrée NAD83 d'origine → famille préservée (EPSG:0).`
    sur une simple couche ontarienne en NAD83.
    """
    ligne = msg.analyse_ligne_datum(famille, 0, action="aucune")
    assert "EPSG:0" not in ligne
    assert "EPSG" not in ligne, "aucun code cible n'a de sens quand rien n'est recommandé"
    assert ligne.startswith("Datum :"), "la famille reste identifiée et dite"


@pytest.mark.parametrize("famille", _TOUTES_LES_FAMILLES)
def test_ligne_datum_rend_toujours_l_epsg_quand_une_cible_existe(famille: str) -> None:
    """Contre-épreuve : hors du cas « aucune », rien ne change.

    Sans elle, supprimer purement et simplement l'EPSG de la fonction ferait
    passer le test ci-dessus — et casserait l'écran nominal en silence.
    """
    ligne = msg.analyse_ligne_datum(famille, 2950, action="zone")
    if famille in {"wgs84", "csrs"}:
        # Ces deux branches n'ont jamais nommé de code cible.
        assert "EPSG" not in ligne
    else:
        assert "EPSG:2950" in ligne


def test_repartition_vide_dit_pourquoi_la_section_est_vide() -> None:
    """DT-22 (N6) : un titre annoncé sans ligne ressemble à un bug de rendu."""
    ligne = msg.analyse_repartition_vide()
    assert "aucun fuseau" in ligne.lower()
    assert "hors" in ligne.lower()


def test_bloc_fuseaux_inchange_pour_zones_a_un_chiffre() -> None:
    """Non-régression (revue B, finitions) : sortie caractère pour caractère identique à
    l'ancienne `analyse_ligne_fuseau(7, 100.0, -70.5)` quand toutes les zones du bloc sont
    à un chiffre — valeur capturée réellement avant le refactor vers `analyse_bloc_fuseaux`."""
    assert msg.analyse_bloc_fuseaux([(7, 100.0, -70.5)]) == [
        "  Fuseau 7 (MC −70,5°)  ████████████████████  100,0 %"
    ]


def test_bloc_fuseaux_aligne_fuseau_9_et_10() -> None:
    """Le Québec a dix fuseaux : « Fuseau 10 » ne doit pas décaler la barre par rapport à
    « Fuseau 9 » (numéro non paddé) — cas réel sur toute couche provinciale (revue B (f))."""
    lignes = msg.analyse_bloc_fuseaux([(9, 58.3, -76.5), (10, 41.7, -79.5)])
    assert len(lignes) == 2
    assert "Fuseau  9" in lignes[0]  # paddé à la largeur de "10"
    assert "Fuseau 10" in lignes[1]
    debut_barre = [ligne.index("█") for ligne in lignes]
    assert debut_barre[0] == debut_barre[1], "les barres ne commencent pas à la même colonne"
