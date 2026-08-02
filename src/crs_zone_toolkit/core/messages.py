"""Toutes les chaînes destinées à l'utilisateur (français), regroupées.

Règle : aucun texte utilisateur en dur ailleurs (feuille_de_route.md §5 — i18n V3).
Le ton et le vocabulaire suivent docs/CLI_UX.md §1 (« fuseau », « famille de
datum », jamais de verdict sec).
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from crs_zone_toolkit.core.results import AnalysisResult, Distorsion

# ── Erreurs (levées, traduites en codes de sortie par la CLI) ──────────────
COUCHE_VIDE = "La couche ne contient aucune entité : il n'y a rien à analyser."
GEOM_IRREPARABLE = (
    "Des géométries sont invalides et n'ont pas pu être réparées (make_valid). "
    "Vérifiez la couche source."
)


def fichier_introuvable(chemin: str) -> str:
    """Message d'erreur : le chemin donné n'est pas un fichier existant (DT-11)."""
    return f"Fichier introuvable : {chemin}. Vérifiez le chemin."


def format_non_supporte(chemin: str) -> str:
    """Message d'erreur : le fichier existe mais n'a pas pu être lu comme couche (DT-11)."""
    return (
        f"Le fichier {chemin} n'a pas pu être lu comme couche vectorielle. "
        "Formats pris en charge : GeoPackage (gpkg), Shapefile (shp), GeoJSON."
    )


def zone_sans_code_famille(zone: int, famille: str) -> str:
    """Erreur DT-18 : le profil n'a pas de code EPSG pour la famille cible au fuseau donné."""
    return (
        f"Profil incomplet : le fuseau {zone} n'a pas de code EPSG pour la famille "
        f"« {famille} ». Recommander une autre famille changerait le datum en silence."
    )


def multi_zones_sans_code_famille(region: str, famille: str) -> str:
    """Erreur DT-18 : multi_zones du profil n'a pas de code pour la famille cible."""
    return (
        f"Profil « {region} » incomplet : multi_zones n'a pas de code EPSG pour la "
        f"famille « {famille} ». Recommander une autre famille changerait le datum en silence."
    )


def crs_absent() -> str:
    """Message pédagogique quand le CRS est absent sans --assume-crs (SPEC §10, [REF-11])."""
    return (
        "Aucun système de coordonnées n'est déclaré par la couche. Impossible "
        "d'analyser sans savoir dans quel CRS sont les coordonnées. Si vous "
        "connaissez le CRS d'origine, relancez avec --assume-crs EPSG:xxxx (cela "
        "ASSIGNE une étiquette, ce n'est pas une reprojection : les coordonnées "
        "ne changent pas)."
    )


# ── Avertissements (portés par AnalysisResult.warnings, jamais levés) ──────
CRS_SUPPOSE = "CRS supposé, non déclaré par la source (fourni via --assume-crs)."
MAKE_VALID_APPLIQUE = "Des géométries invalides ont été réparées (make_valid) avant l'analyse."
NAD27_NTV2 = (
    "Entrée en NAD27 (datum obsolète) : la cible recommandée est en NAD83(CSRS) ; "
    "une transformation de datum NTv2 sera appliquée à l'apply."
)
# N21 : cette note suivait la ligne « Datum : … famille préservée » en la
# répétant mot pour mot ; seule sa fin apportait quelque chose. Réduite à ce
# qu'elle ajoute, et complétée de l'ordre de grandeur — c'est ce mètre qui rend
# le conseil actionnable, et le rapport HTML le donnait déjà (`NOTE_DATUM`).
# Sa formulation n'a plus de coût de contrat : depuis DT-26 elle ne transite
# ni par le JSON ni par le rapport.
CSRS_STANDARD_ACTUEL = (
    "Note : NAD83(CSRS) est le standard actuel des données québécoises — écart ≈ 1 m."
)

# ── DT-26 : le marqueur signale ce qui BOUGE, pas ce qui reste ────────────
# Avant, `_datum_warnings` mettait un ⚠ sur la PRÉSERVATION (NAD83, le cas le
# moins risqué) et rien sur le CHANGEMENT de famille (WGS 84 → CSRS, un écart
# d'environ un mètre au Québec). La marque vit désormais sur la ligne « Datum :»
# elle-même : c'est là que le fait est énoncé, et l'ancien avertissement NAD83
# ne faisait que répéter cette ligne.
MARQUE_DATUM_PRESERVE = "preserve"
MARQUE_DATUM_CHANGE = "change"


def marque_datum(famille: str, famille_cible: str) -> str:
    """Nature de la ligne « Datum : » — préservation ou changement de famille.

    Renvoie une **valeur symbolique**, pas un caractère : le choix du glyphe et
    de la couleur appartient à `affichage` (ce module reste sans balisage Rich).
    """
    return MARQUE_DATUM_PRESERVE if famille == famille_cible else MARQUE_DATUM_CHANGE


def analyse_note_datum(famille: str) -> str | None:
    """Conseil neutre accompagnant la ligne « Datum : », ou None.

    « NAD83(CSRS) est le standard actuel » est un **conseil**, pas une alerte :
    il ne signale aucun risque, il informe. D'où sa sortie des avertissements
    (DT-26). La chaîne elle-même est conservée telle quelle — elle transite par
    le rapport HTML validé le 17/07 (divergence DT-20 (3)).
    """
    return CSRS_STANDARD_ACTUEL if famille == "nad83" else None


def envelopper(texte: str, largeur: int, tete: str) -> list[str]:
    """Découpe `texte` en lignes de `largeur` max, suites alignées SOUS le texte (N18).

    Le défaut corrigé : Rich enveloppait sans retrait de continuation, donc
    toute ligne qui débordait reprenait en **colonne 0**. « Note : NAD83(CSRS)
    est le standard actuel. » venait se coller à la marge gauche sous un `⚠`
    indenté ; la fin d'un `✓ Sortie` ou d'un `Motif :` aussi. Visible dans
    presque tous les blocs du protocole de test, et sur la première page du
    README.

    `tete` est le préfixe **en clair** de la première ligne (`"  "`, `"  ⚠ "`,
    `"→ "`…). Les suivantes reçoivent autant d'espaces : l'alignement se fait
    sous le texte, jamais sous le glyphe. L'appelant réapplique ensuite le
    balisage Rich sur le glyphe — ce module reste sans balisage.

    `break_long_words=False` : un chemin de fichier coupé en deux n'est plus
    copiable. Mieux vaut le laisser déborder (le terminal l'enveloppera comme
    avant) que le rendre inutilisable.
    """
    retrait = " " * len(tete)
    lignes = textwrap.wrap(
        texte,
        width=largeur,
        initial_indent=tete,
        subsequent_indent=retrait,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return lignes or [tete.rstrip() or ""]


def hors_profil(part: float) -> str:
    """« x % hors profil » (SPEC §4.3.6)."""
    return (
        f"{round(part * 100)} % des données tombent hors du profil : aucune "
        "recommandation pour cette part."
    )


def note_reconnu(etiquette: str) -> str:
    """Note d'identification d'un CRS en circulation reconnu (DATA_REFERENCE §4.2)."""
    return f"CRS reconnu : {etiquette} (identifié, non recommandé comme cible)."


def libelle_fuseau(zone: int) -> str:
    """Libellé lisible d'un fuseau MTM (chaîne utilisateur → messages.py)."""
    return f"MTM fuseau {zone}"


def libelle_candidat_fuseau(zone: int, *, multi_fuseaux: bool) -> str:
    """Libellé du candidat « fuseau » dans le tableau de distorsion (CLI_UX §3).

    Le suffixe « (tout) » dit que la distorsion de ce fuseau est mesurée sur
    **toute** la couche, y compris ses parts situées **hors de ce fuseau** — par
    opposition au découpage, où chaque morceau serait mesuré dans le sien. Sans
    lui, un chiffre comme 14 784 ppm se lit comme une erreur (DT-20 (1)).

    Il ne paraît **que si plusieurs fuseaux sont traversés** : sur une couche
    mono-fuseau, « tout » n'oppose rien à rien et n'est que du bruit.

    À ne pas confondre avec l'exclusion de DT-24, qui écarte le hors-**profil**
    et non le hors-**fuseau** : une couche étalée fait toujours grimper la
    valeur du candidat dominant, et c'est ce que ce suffixe annonce.
    """
    return f"{libelle_fuseau(zone)} (tout)" if multi_fuseaux else libelle_fuseau(zone)


def motif_mono_zone(zone: int) -> str:
    return f"Les données tiennent dans un seul fuseau (MTM {zone})."


def motif_zone_dominante(zone: int, part: float, ppm: float) -> str:
    return (
        f"Le fuseau MTM {zone} concentre {round(part * 100)} % des données avec une "
        f"distorsion maîtrisée ({round(ppm)} ppm max)."
    )


def motif_hors_profil_total() -> str:
    return "Toutes les données tombent hors du profil : aucune recommandation possible."


def motif_zone_moins_deformee(zone: int, ppm: float, seuil: float, *, decoupage_utile: bool) -> str:
    """Motif « meilleure projection unique, mais au-delà de la tolérance ».

    `decoupage_utile` — vrai seulement si le découpage produirait **plusieurs**
    fichiers. Sinon, promettre qu'il « garde chaque morceau sous le seuil » est
    **faux** : toutes les entités relevant majoritairement d'un seul fuseau, le
    découpage rendrait un fichier unique, à la même distorsion (N23). Mesuré sur
    la SDA : 12 régions multi-fuseaux sur 13 sont dans ce cas.
    """
    tete = (
        f"Le fuseau MTM {zone} est la projection unique la moins déformée "
        f"({round(ppm)} ppm max), mais dépasse la tolérance ({round(seuil)} ppm)"
    )
    if decoupage_utile:
        return f"{tete} : le découpage par fuseau garde chaque morceau sous le seuil."
    return (
        f"{tete}. Le découpage n'aiderait pas : toutes les entités relèvent "
        f"majoritairement du même fuseau."
    )


def motif_lambert_moins_deforme(
    zone: int, ppm_zone: float, ppm_lambert: float, *, decoupage_utile: bool
) -> str:
    """Motif « le Lambert l'emporte ». Même garde que ci-dessus (N23) : annoncer un
    découpage « disponible en alternative » est faux quand il ne découperait rien."""
    tete = (
        f"Les données sont trop étendues pour le fuseau dominant (MTM {zone} : "
        f"{round(ppm_zone)} ppm) : le Québec Lambert est la projection unique la "
        f"moins déformée ({round(ppm_lambert)} ppm max)."
    )
    if decoupage_utile:
        return f"{tete} Découpage disponible en alternative."
    return f"{tete} Le découpage n'aiderait pas : toutes les entités relèvent du même fuseau."


# ── apply (Jalon J3) ───────────────────────────────────────────────────────
AVERTISSEMENT_SHP = (
    "Format Shapefile : noms de champs tronqués à 10 caractères et taille limitée. "
    "GeoPackage (gpkg) est recommandé."
)
NOTE_CHOIX_HORS_RECO = "choix utilisateur ≠ recommandation"


def fichier_existant(chemin: str) -> str:
    """Message d'avertissement : le fichier de sortie existe déjà."""
    return f"Le fichier de sortie existe déjà : {chemin}. Utilisez --overwrite pour l'écraser."


def format_sortie_invalide(fmt: str, valides: list[str]) -> str:
    """Erreur DT-06 : format de sortie inconnu passé à l'API apply."""
    return f"Format de sortie inconnu : « {fmt} ». Formats pris en charge : {', '.join(valides)}."


def grille_absente(grilles: tuple[str, ...], datum_source: str, datum_cible: str) -> str:
    """Message d'erreur : transformation de datum requise mais grille(s) PROJ absente(s).

    Nomme la ou les grilles réellement manquantes (extraites du TransformerGroup par
    l'appelant) plutôt qu'un nom codé en dur : la grille requise dépend de la paire de
    datums (p. ex. ca_nrc_NA27SCRS.tif pour NAD27 → NAD83(CSRS), ca_nrc_NA83SCRS.tif
    pour NAD83(CSRS) → NAD83(CSRS)v2), et un mauvais nom conseillerait le mauvais fichier.
    """
    liste = ", ".join(grilles) if grilles else "(grille non identifiée)"
    return (
        f"Transformation de datum requise ({datum_source} → {datum_cible}) mais la ou les "
        f"grilles PROJ nécessaires sont absentes : {liste}. Installez-les via proj-data "
        "(https://proj.org/en/stable/usage/network.html) plutôt qu'un téléchargement silencieux ; "
        "sans elles, seule une transformation approximative (« ballpark ») serait possible, "
        "ce que l'outil refuse."
    )


def approximation_acceptee(grilles: tuple[str, ...], datum_source: str, datum_cible: str) -> str:
    """Avertissement : repli « ballpark » accepté entre familles de datum modernes (DT-01).

    Jamais silencieux : le message nomme les deux datums et la grille absente,
    et il est journalisé via ApplyResult.avertissements (SPEC §9).
    """
    liste = ", ".join(grilles) if grilles else "(grille non identifiée)"
    return (
        f"Transformation de datum approximative acceptée ({datum_source} → {datum_cible}) : "
        f"la grille PROJ {liste} est absente. Ces familles ne sont pas déclarées comme "
        "exigeant une transformation exacte dans le profil ; l'écart entre elles est "
        "négligeable devant la précision d'une reprojection cartographique. Pour la "
        "transformation exacte, installez la grille via proj-data. Décision journalisée."
    )


def hors_profil_affecte(zone: int) -> str:
    """Message d'information : une entité hors profil a été affectée au fuseau le plus proche."""
    return f"Une entité hors du profil a été affectée au fuseau le plus proche (MTM {zone})."


# ── Rapport HTML (J4) ──────────────────────────────────────────────────────

ALT_SPLIT_TITRE = "Découpage par fuseau"

FAMILLE_LIBELLE = {
    "nad83": "NAD83 d'origine",
    "csrs": "NAD83(CSRS)",
    "nad27": "NAD27",
    "wgs84": "WGS84",
    "autre": "Autre datum",
}
FAMILLE_LIBELLE_DEFAUT = "Autre datum"


def alt_split_desc(zones: list[int]) -> str:
    liste = ", ".join(str(z) for z in zones)
    return (
        f"Une couche par fuseau ({liste}), chaque entité affectée au fuseau où sa "
        "grandeur dominante est majoritaire (entités intactes, jamais coupées). "
        "Précision MTM maximale par sortie, au prix de plusieurs fichiers et de "
        "mesures inter-fuseaux impossibles directement."
    )


NOTE_DATUM = {
    "nad83": (
        "La couche est en NAD83 d'origine. La famille est préservée dans la "
        "recommandation (aucun changement de datum silencieux) ; NAD83(CSRS) est le "
        "standard actuel des données québécoises (écart ≈ 1 m). Une migration "
        "éventuelle sera une transformation contrôlée et journalisée."
    ),
    "nad27": (
        "La couche est en NAD27, un datum historique. Passer à NAD83(CSRS) exige une "
        "transformation de datum par grille NTv2 — jamais appliquée silencieusement."
    ),
    "csrs": (
        "La couche est en NAD83(CSRS), le standard géodésique actuel du Québec : "
        "aucune transformation de datum n'est nécessaire."
    ),
    "wgs84": (
        "La couche est en WGS84. Pour des mesures métriques au Québec, une projection "
        "du profil est recommandée ; la famille n'est pas modifiée silencieusement."
    ),
    "autre": (
        "La famille de datum de la couche n'est pas reconnue par le profil. Aucune "
        "transformation de datum n'est appliquée silencieusement : vérifiez "
        "manuellement le datum d'origine avant toute reprojection."
    ),
}
NOTE_DATUM_DEFAUT = NOTE_DATUM["autre"]


# ── CLI (Jalon J5) ─────────────────────────────────────────────────────────
CLI_AIDE = "crszone — analyse, recommandation et reprojection CRS pour le Québec (MTM / Lambert)."
CLI_AIDE_REGION = "Profil de région à utiliser (défaut : qc)."
CLI_AIDE_ANALYZE = (
    "Analyser une couche : fuseaux traversés, distorsion, recommandation (lecture seule)."
)
CLI_AIDE_APPLY = "Reprojeter ou découper après confirmation (analyser → décider → agir)."
CLI_AIDE_GRID = "Générer la grille des fuseaux MTM du profil."


def grille_entete() -> str:
    return "Grille des fuseaux MTM — profil Québec (qc)"


def grille_ligne_decoupe(clip: bool) -> str:
    if clip:
        return (
            "  9 fuseaux (2 à 10) · bandes de 3° · découpe : limite du Québec (SDA MRNF, CC-BY 4.0)"
        )
    return "  9 fuseaux (2 à 10) · bandes de 3° · bandes complètes (57°O → 81°O, non découpées)"


def grille_ligne_ecrite(chemin: str, n: int, attributs: tuple[str, ...]) -> str:
    """Ligne de confirmation d'écriture de la grille (CLI_UX §7)."""
    return f"{chemin} ({fr_accord(n, 'entité')}, attributs : {', '.join(attributs)})"


# ── CLI analyze — résumé terminal (CLI_UX §2/§3, Jalon J5) ─────────────────


def fr_nombre(x: float, dec: int = 1) -> str:
    """Nombre en notation française : milliers par espace (U+0020), virgule décimale.

    Point de vérité unique du format numérique FR (DT-05) — report._fr,
    _fr_entier et _fr_deg délèguent ici.
    """
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def _fr_entier(n: int) -> str:
    """Entier avec espace de milliers (CLI_UX §2 : « 1 842 ») — délègue à fr_nombre (DT-05)."""
    return fr_nombre(n, dec=0)


def _fr_deg(valeur: float) -> str:
    """Valeur absolue à 2 décimales, virgule française (ligne Emprise) — délègue (DT-05)."""
    return fr_nombre(abs(valeur), dec=2)


_TYPE_GEOMETRIE_LIBELLE = {"point": "points", "line": "lignes", "polygon": "polygones"}


def analyse_entete(profil_nom: str, profil_id: str) -> str:
    """Titre du résumé (CLI_UX §2/§3 : « Analyse CRS — profil Québec (qc) »)."""
    return f"Analyse CRS — profil {profil_nom} ({profil_id})"


def analyse_version(version: str) -> str:
    """Mention de version alignée à droite de l'en-tête (CLI_UX §2)."""
    return f"crszone {version}"


def fr_accord(n: int, singulier: str, pluriel: str | None = None) -> str:
    """« 1 entité » / « 21 entités » — en français seul **1** est singulier (0 est pluriel).

    Le nombre lui-même passe par `fr_nombre` (DT-05, point de vérité unique du
    format numérique) ; cette fonction ne décide que du mot.
    """
    mot = singulier if abs(n) == 1 else (pluriel if pluriel is not None else singulier + "s")
    return f"{_fr_entier(n)} {mot}"


def analyse_ligne_couche(nom: str, type_geometrie: str, n_entites: int) -> str:
    """Ligne « Couche … (n entités, type) » — effectif ajouté (DT-02)."""
    libelle_type = _TYPE_GEOMETRIE_LIBELLE.get(type_geometrie, type_geometrie)
    return f"Couche      {nom} ({fr_accord(n_entites, 'entité')}, {libelle_type})"


def analyse_ligne_crs_declare(epsg: int | None, etiquette: str, *, geographique: bool) -> str:
    """Ligne « CRS déclaré … » — suffixe « (géographique) » quand le CRS n'est pas projeté
    (CLI_UX §2/§3 : le lecteur doit voir immédiatement qu'aucune mesure métrique n'est possible)."""
    suffixe = " (géographique)" if geographique else ""
    if epsg is not None:
        return f"CRS déclaré EPSG:{epsg} — {etiquette}{suffixe}"
    # DT-26 (N13) : sans code EPSG résolu, l'écran enchaînait « CRS déclaré
    # unknown » puis « Datum : entrée WGS 84 → … ». Les deux sont exacts et
    # parlent de niveaux différents — le CODE du CRS est irrésoluble, son DATUM
    # est lisible — mais rien ne le disait, et un lecteur peut y voir une
    # contradiction. Le renvoi tient sur la ligne (N18 : pas de débordement).
    return f"CRS déclaré {etiquette}{suffixe} — aucun code EPSG résolu, datum ci-dessous"


def analyse_ligne_emprise(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> str:
    """Ligne « Emprise … » (DT-02) : degrés signés WGS84, lettre cardinale + valeur absolue."""

    def _lon(v: float) -> str:
        return f"{_fr_deg(v)}°{'O' if v < 0 else 'E'}"

    def _lat(v: float) -> str:
        return f"{_fr_deg(v)}°{'N' if v >= 0 else 'S'}"

    return f"Emprise     {_lon(lon_min)} → {_lon(lon_max)} · {_lat(lat_min)} → {_lat(lat_max)}"


_REPARTITION_GRANDEUR = {
    "polygon": "part de la surface totale",
    "line": "part de la longueur totale",
    "point": "part de l'effectif total",
}


def analyse_repartition_titre(type_geometrie: str) -> str:
    """Titre de la répartition, avec la grandeur réellement mesurée (CLI_UX §3, SPEC §4.2.3)."""
    grandeur = _REPARTITION_GRANDEUR.get(type_geometrie)
    return f"Répartition par fuseau MTM ({grandeur})" if grandeur else "Répartition par fuseau MTM"


def analyse_repartition_vide() -> str:
    """Ligne unique sous le titre de répartition quand aucun fuseau n'est traversé (DT-22).

    Sans elle, le titre s'affiche seul : un géomaticien le lit comme un bug de
    rendu, pas comme un fait sur ses données (observation N6 du test manuel).

    Formulée dans les termes **de la section** (l'emprise contre la grille), et
    non comme un second énoncé du verdict : la ligne « Recommandation : aucune »
    dit déjà ce dernier, deux lignes plus bas — vérifié sur la sortie réelle.
    """
    return "Aucun fuseau traversé — l'emprise tombe hors de la grille du profil."


def analyse_distorsion_titre(n_echantillons_effectif: int) -> str:
    """En-tête du tableau de distorsion (DT-02) : N = nombre RÉEL de points mesurés,
    jamais le plafond `n_echantillons` (chantier A, `parametres.n_echantillons_effectif`)."""
    return f"Distorsion mesurée ({_fr_entier(n_echantillons_effectif)} points d'échantillonnage)"


_BARRE_LARGEUR = 20  # 20 caractères = 100 % (échelle de la maquette CLI_UX §2/§3)


def _fr_degre_signe(valeur: float) -> str:
    """Degré signé à la française : « −70,5° » (signe moins U+2212, virgule décimale)."""
    signe = "−" if valeur < 0 else ""
    return f"{signe}{fr_nombre(abs(valeur), dec=1)}°"


def analyse_bloc_fuseaux(lignes: Sequence[tuple[int, float, float]]) -> list[str]:
    """Bloc de lignes « Fuseau N (MC −70,5°)  ████…  xx,x % » (CLI_UX §2/§3).

    `lignes` : `(zone, part_pct, meridien_central)`. Le numéro de zone est paddé
    sur la largeur du plus grand numéro présent dans le bloc, pour que les
    barres commencent toutes à la même colonne — le Québec a dix fuseaux, et
    « Fuseau 10 » ne doit pas décaler la barre par rapport à « Fuseau 7 »
    (revue B (f), cas réel sur toute couche provinciale). Sortie caractère
    pour caractère identique à l'ancienne `analyse_ligne_fuseau` quand toutes
    les zones du bloc sont à un chiffre.

    Le méridien central vient du profil injecté — aucune valeur géodésique ici (TP-40).
    """
    largeur_zone = max((len(str(zone)) for zone, _, _ in lignes), default=1)
    resultat = []
    for zone, part_pct, meridien_central in lignes:
        barre = "█" * round(part_pct / 100 * _BARRE_LARGEUR)
        resultat.append(
            f"  Fuseau {zone:>{largeur_zone}} (MC {_fr_degre_signe(meridien_central)})  "
            f"{barre:<{_BARRE_LARGEUR}}  {fr_nombre(part_pct, dec=1).rjust(5)} %"
        )
    return resultat


def _ppm_affiche(valeur: float) -> str:
    """Valeur ppm signée pour le terminal : « +41 ppm », « −100 ppm » (U+2212, CLI_UX §1)."""
    # N7 : le signe était choisi sur la valeur BRUTE, puis l'arrondi l'effaçait —
    # d'où le « −0 ppm » relevé au test. On arrondit d'abord, on signe ensuite ;
    # un zéro n'a pas de signe.
    arrondi = round(valeur)
    if arrondi == 0:
        return "0 ppm"
    signe = "−" if arrondi < 0 else "+"
    return f"{signe}{abs(arrondi):.0f} ppm"


def analyse_bloc_distorsion(distorsions: Sequence[Distorsion], seuil_ppm: float) -> list[str]:
    """Tableau « Distorsion mesurée » avec en-tête de colonnes (CLI_UX §2/§3).

    Les colonnes sont dimensionnées sur le contenu réel (libellés et codes de longueurs
    variables : « MTM fuseau 7 » vs « Québec Lambert », EPSG:2949 vs EPSG:26899 ; valeurs
    ppm de « −100 ppm » à des distorsions extrêmes comme « +15793 ppm » sur des données
    réelles hors profil). La largeur ppm a un plancher de 9 (largeur de la maquette
    CLI_UX §2/§3) : elle ne s'élargit que si une valeur mesurée l'exige, pour que le rendu
    des données normales reste identique à la maquette. Le marqueur « hors seuil » reprend
    le critère de gating `max(|min|,|max|)` (SPEC §4.3) : c'est un miroir d'affichage,
    jamais une re-décision (cf. D-J4-7).
    """
    codes = [f"EPSG:{d.epsg}" for d in distorsions]
    lib_w = max((len(d.libelle) for d in distorsions), default=len("Candidat"))
    lib_w = max(lib_w, len("Candidat"))
    code_w = max((len(c) for c in codes), default=0)
    ppm_w = max(
        (len(_ppm_affiche(v)) for d in distorsions for v in (d.min_ppm, d.moy_ppm, d.max_ppm)),
        default=9,
    )
    ppm_w = max(ppm_w, 9)

    lignes = [
        f"  {'Candidat':<{lib_w}} {'':<{code_w}}  "
        f"{'min':>{ppm_w}}  {'moy':>{ppm_w}}  {'max':>{ppm_w}}".rstrip()
    ]
    for d, code in zip(distorsions, codes, strict=True):
        hors = max(abs(d.min_ppm), abs(d.max_ppm)) > seuil_ppm
        ligne = (
            f"  {d.libelle:<{lib_w}} {code:<{code_w}}  "
            f"{_ppm_affiche(d.min_ppm):>{ppm_w}}  "
            f"{_ppm_affiche(d.moy_ppm):>{ppm_w}}  "
            f"{_ppm_affiche(d.max_ppm):>{ppm_w}}"
        )
        lignes.append(f"{ligne}  ⚠ hors seuil" if hors else ligne)
    return lignes


def analyse_recommandation(
    action: str, cible_libelle: str, cible_epsg: int, famille_libelle: str
) -> str:
    """Ligne « → Recommandation … » (CLI_UX §2/§3).

    `action == "aucune"` : 100 % hors profil, `cible_epsg` vaut la sentinelle 0
    (SPEC §8) — on n'affiche jamais « EPSG:0 », qui n'est pas un code valide.
    """
    if action == "aucune":
        return "Recommandation : aucune — toutes les données tombent hors du profil."
    return (
        f"Recommandation : reprojeter vers {cible_libelle} (EPSG:{cible_epsg}, {famille_libelle})"
    )


def analyse_motif(motif: str) -> str:
    return f"Motif : {motif}"


def analyse_ligne_datum(famille: str, cible_epsg: int, *, action: str) -> str:
    """Ligne « Datum : … » sous la recommandation (CLI_UX §2 : WGS84 → défaut ;
    §3 : NAD83 → famille préservée). Couvre wgs84/nad83/csrs/nad27/autre.

    `action == "aucune"` : 100 % hors profil, `cible_epsg` vaut la sentinelle 0
    (SPEC §8) — **aucune branche ne nomme alors de code cible** (DT-22). La
    famille reste identifiée et dite : c'est une information juste, et la seule
    que l'écran puisse encore donner. Les branches `wgs84` et `csrs` n'ont
    jamais nommé de code : les trois autres prennent ici la même forme.

    `action` est **obligatoire et nommé** : un défaut laisserait un site d'appel
    reconduire le défaut en silence, ce qui est précisément comment `EPSG:0` a
    survécu au test de non-régression du protocole §5.
    """
    aucune = action == "aucune"
    if famille == "wgs84":
        return "Datum : entrée WGS 84 → famille CSRS par défaut."
    if famille == "nad83":
        libelle = FAMILLE_LIBELLE["nad83"]
        code = "" if aucune else f" (EPSG:{cible_epsg})"
        return f"Datum : entrée {libelle} → famille préservée{code}."
    if famille == "csrs":
        libelle = FAMILLE_LIBELLE["csrs"]
        return f"Datum : entrée {libelle} → déjà la famille standard, aucune transformation."
    if famille == "nad27":
        libelle = FAMILLE_LIBELLE["nad27"]
        grille = "(grille NTv2)" if aucune else f"(grille NTv2, EPSG:{cible_epsg})"
        return f"Datum : entrée {libelle} → transformation vers NAD83(CSRS) {grille}."
    code = "" if aucune else f" (EPSG:{cible_epsg})"
    return f"Datum : entrée {FAMILLE_LIBELLE_DEFAUT} → famille CSRS par défaut{code}."


def apply_mode_auto(cible_libelle: str, cible_epsg: int, *, action: str) -> str:
    """Ligne annonçant le mode automatique (CLI_UX §5, observation N4).

    Sans elle, une sortie `--auto` ne se distingue d'un choix humain qu'en
    relisant `decision.origine` dans le journal.

    `action == "aucune"` : aucune cible n'existe, et la sentinelle `cible_epsg`
    vaut 0 — la ligne ne nomme alors **aucun** code, même leçon que DT-22.
    """
    if action == "aucune":
        return "Mode --auto : aucune recommandation à appliquer — aucune sortie écrite."
    return f"Mode --auto : application de la recommandation ({cible_libelle}, EPSG:{cible_epsg})."


def analyse_ligne_alternative_split(n_sorties: int) -> str:
    """Ligne « Alternative : découpage par fuseau … » (CLI_UX §3), condensée depuis
    `alt_split_desc` — émise seulement si `recommandation.alternatives` contient un
    découpage (`action == "split"`)."""
    return (
        f"Alternative : découpage par fuseau ({fr_accord(n_sorties, 'sortie')}, entités "
        "affectées au fuseau majoritaire)."
    )


def analyse_rapport(nom_fichier: str) -> str:
    """Ligne de confirmation d'écriture du rapport (CLI_UX §2/§3)."""
    return f"Rapport détaillé : {nom_fichier}"


def analyse_pour_appliquer(nom_couche: str) -> str:
    return f"Pour appliquer : crszone apply {nom_couche}"


def assume_crs_bandeau(code: str) -> str:
    """Bandeau permanent « CRS supposé » (CLI_UX §6.2)."""
    return f"CRS SUPPOSÉ : {code} fourni par --assume-crs, non déclaré par la source."


ASSUME_CRS_TRACE = "L'hypothèse est tracée dans le rapport et le journal."


# ── CLI apply (Jalon J5) ────────────────────────────────────────────────────
NON_INTERACTIF = (
    "Session non interactive : impossible de demander une confirmation. Utilisez "
    "--auto (appliquer la recommandation) ou --choice zone|lambert|split."
)
APPLY_ANNULE = (
    "Analyse conservée, aucune donnée écrite. Relancez crszone apply quand vous aurez décidé."
)


def apply_annule(chemin_rapport: Path | None) -> str:
    """Message d'annulation `[0]` (CLI_UX §4), nommant le rapport à relire (DT-23).

    Le menu dit « Annuler (relire le rapport avant de décider) » : sans le
    chemin, l'utilisateur sait qu'un rapport existe mais pas où. Et « aucune
    donnée écrite » resterait vrai tout en passant sous silence le fichier qui
    vient d'être produit.

    `None` — hors du périmètre où `apply` écrit un rapport : message inchangé.
    """
    if chemin_rapport is None:
        return APPLY_ANNULE
    return (
        f"Analyse conservée, aucune donnée écrite. Rapport à relire : {chemin_rapport.name}. "
        "Relancez crszone apply quand vous aurez décidé."
    )


def zone_invalide(zone: int) -> str:
    """Message d'erreur : le fuseau demandé (--zone) n'existe pas dans le profil."""
    return f"Fuseau {zone} inconnu du profil : choisissez un fuseau valide."


def choix_invalide(choix: str) -> str:
    """Message : valeur de --choice non reconnue."""
    return (
        f"Valeur de --choice non reconnue : {choix!r}. "
        "Attendu : recommendation, zone, lambert ou split."
    )


def zone_absente() -> str:
    """Message : --choice zone demandé mais aucun fuseau traversé (données hors profil)."""
    return (
        "Aucun fuseau traversé (données hors du profil) : --choice zone est impossible ; "
        "précisez --zone ou choisissez lambert."
    )


def format_invalide(fmt: str, autorises: tuple[str, ...]) -> str:
    """Message : valeur de --format non reconnue."""
    return f"Format non reconnu : {fmt!r}. Formats acceptés : {', '.join(autorises)}."


def apply_ligne_sortie(chemin: str, epsg: int, n_entites: int) -> str:
    """Ligne « Sortie : <chemin> (EPSG:xxxx, n entités) » (écran de succès d'apply)."""
    return f"Sortie   : {chemin} (EPSG:{epsg}, {fr_accord(n_entites, 'entité')})"


def apply_ligne_journal(chemin: str) -> str:
    return f"Journal  : {chemin}"


def apply_ligne_pipeline(pipeline: str) -> str:
    return f"  Pipeline PROJ : {pipeline}"


def apply_menu(result: AnalysisResult) -> list[str]:
    """Lignes du menu interactif (CLI_UX §4). result : AnalysisResult."""
    reco = result.recommandation
    # `[2]` propose de reprojeter vers n'importe quel fuseau TRAVERSÉ — c'est bien
    # la bonne liste ici.
    zones = ", ".join(str(z.zone) for z in result.zones_traversees)
    # `[3]` annonce des FICHIERS : il lit le même `alternatives[split].zones` que la
    # ligne « Alternative » du résumé (DT-25). Les deux paraissent sur le MÊME écran
    # de décision — les laisser compter chacun de leur côté, c'était les laisser se
    # contredire (`regio_s` : 6 contre 9).
    alt_split = next((a for a in reco.alternatives if a.get("action") == "split"), None)
    lignes = [
        # N2 bis : le résumé et le menu se touchaient, sur un écran de DÉCISION.
        "",
        "Que voulez-vous faire ?",
        f"  [1] Appliquer la recommandation — {reco.cible_libelle} (EPSG:{reco.cible_epsg})",
        f"  [2] Reprojeter vers un fuseau MTM unique (préciser : {zones})",
    ]
    # N20 : `[3]` n'est proposé que si le découpage produit plusieurs fichiers.
    # Sur une sortie unique il est identique à `[2]` sur le fuseau majoritaire :
    # du bruit sur un écran de décision. L'absence d'alternative dans la
    # recommandation est la source de vérité — menu et résumé ne peuvent pas
    # diverger (leçon de la miss de DT-25).
    if alt_split is not None:
        n = len(alt_split["zones"])
        lignes.append(
            f"  [3] Découper par fuseau MTM — affectation majoritaire, {fr_accord(n, 'sortie')}"
        )
    lignes.append("  [0] Annuler (relire le rapport avant de décider)")
    return lignes


APPLY_INVITE = "Votre choix"
APPLY_INVITE_FUSEAU = "Quel fuseau ?"


def apply_hors_seuil(valeur_ppm: float) -> str:
    """Rappel affiché quand le fuseau choisi dépasse le seuil de distorsion (CLI_UX §4).

    `valeur_ppm` est la valeur qui FRANCHIT réellement le seuil — soit le min, soit
    le max de la distorsion mesurée, celui dont la valeur absolue est la plus grande
    (DT-03 : l'ancien code affichait toujours `max_ppm`, même quand c'était le min
    qui dépassait)."""
    return f"distorsion max {valeur_ppm:+.0f} ppm hors seuil"
