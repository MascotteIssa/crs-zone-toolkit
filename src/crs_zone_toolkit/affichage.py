"""Rendu Rich des écrans CLI (aucune logique métier — présentation seule).

Toutes les chaînes proviennent de core.messages ; ce module ne fait que les
disposer avec Rich. Les maquettes exactes sont dans docs/CLI_UX.md.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

import crs_zone_toolkit
from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.profile import RegionProfile
from crs_zone_toolkit.core.results import AnalysisResult, ApplyResult


def _ligne(console: Console, texte: str, *, tete: str = "", glyphe: str = "") -> None:
    """Imprime une ligne dont les retours s'alignent SOUS le texte (N18, DT-29).

    `tete` est le préfixe en clair (« ␣␣ », « ␣␣⚠␣ »…) ; `glyphe` est son
    équivalent balisé Rich, appliqué à la seule première ligne. Le découpage
    lui-même vit dans `messages.envelopper` : il est ainsi testable comme une
    fonction pure, sans passer par une console (TEST_PLAN §5).
    """
    lignes = msg.envelopper(texte, largeur=console.width, tete=tete)
    premiere = lignes[0]
    console.print(f"{glyphe}{premiere[len(tete) :]}" if glyphe else premiere)
    for suite in lignes[1:]:
        if len(suite) <= console.width:
            console.print(suite)
            continue
        # Jeton insécable plus long que la console (un chemin de fichier) :
        # `envelopper` le laisse entier exprès — coupé, il n'est plus copiable.
        # Rich le coupera donc quand même, mais `Padding` lui fait garder le
        # retrait au lieu de le renvoyer en colonne 0, qui est tout le sujet de N18.
        console.print(Padding(Text(suite.lstrip()), (0, 0, 0, len(tete))))


def message(console: Console, texte: str) -> None:
    """Ligne d'information simple, enveloppée sans débordement (N18)."""
    _ligne(console, texte)


def erreur(console: Console, texte: str) -> None:
    """Ligne d'erreur « ✗ … » — nommée par N18, qui l'avait relevée débordante."""
    _ligne(console, texte, tete="✗ ", glyphe="[red]✗[/red] ")


def resume_grille(
    console: Console, chemin: Path, n: int, attributs: tuple[str, ...], *, clip: bool
) -> None:
    """Écran de la commande grid (CLI_UX §7)."""
    console.print(msg.grille_entete())
    console.print(msg.grille_ligne_decoupe(clip))
    console.print(f"[green]✓[/green] {msg.grille_ligne_ecrite(str(chemin), n, attributs)}")


def bandeau_assume_crs(console: Console, code: str) -> None:
    """Bandeau permanent « CRS supposé » (CLI_UX §6.2, 2 lignes)."""
    _ligne(console, msg.assume_crs_bandeau(code), tete="⚠ ", glyphe="[yellow]⚠[/yellow] ")
    _ligne(console, msg.ASSUME_CRS_TRACE, tete="  ")


def resume_analyse(
    console: Console,
    result: AnalysisResult,
    chemin_rapport: Path | None,
    *,
    couche: Path,
    n_entites: int,
    profile: RegionProfile,
    crs_geographique: bool,
    famille_cible: str,
    abrege: bool = False,
    suggerer_apply: bool = True,
) -> None:
    """Résumé terminal d'une analyse (CLI_UX §2/§3/§5).

    `chemin_rapport` est optionnel : `apply` n'écrit aucun rapport HTML (seule `analyze`
    en écrit un, cf. `cli.py`) ; quand il vaut `None`, la ligne « Rapport détaillé » est
    omise (DT-20 n°5) — la ligne « Pour appliquer » qui suit reste affichée.

    `suggerer_apply` : la ligne « Pour appliquer : crszone apply … » ne s'adresse
    qu'au lecteur d'une **analyse**. `apply` la passe à False — elle y proposait la
    commande en cours (N2, DT-29).

    `famille_cible` (« csrs »/« nad83 ») vient de l'appelant (`target_family(result.famille)`,
    importé localement dans `cli.py`) : ce module ne doit charger ni `geopandas` ni `pyproj`
    (finitions revue B (e)) — seul le libellé est résolu ici, via `msg.FAMILLE_LIBELLE`.
    """
    reco = result.recommandation
    entete = Table.grid(expand=True)  # titre à gauche, version à droite (CLI_UX §2)
    entete.add_column(justify="left")
    entete.add_column(justify="right")
    entete.add_row(
        f"[bold]{msg.analyse_entete(profile.nom, profile.id)}[/bold]",
        msg.analyse_version(crs_zone_toolkit.__version__),
    )
    console.print(entete)
    console.print(Rule(style="dim"))
    _ligne(console, msg.analyse_ligne_couche(couche.name, result.type_geometrie, n_entites))
    crs = result.crs_entree
    _ligne(
        console,
        msg.analyse_ligne_crs_declare(
            crs.get("epsg"), str(crs.get("etiquette", "")), geographique=crs_geographique
        ),
    )
    emprise = result.emprise
    console.print(
        msg.analyse_ligne_emprise(
            emprise.lon_min, emprise.lat_min, emprise.lon_max, emprise.lat_max
        )
    )
    if not abrege:
        console.print()
        console.print(msg.analyse_repartition_titre(result.type_geometrie))
        mc_par_zone = {f.zone: f.meridien_central for f in profile.fuseaux}
        if result.zones_traversees:
            for ligne in msg.analyse_bloc_fuseaux(
                [(zp.zone, zp.part * 100, mc_par_zone[zp.zone]) for zp in result.zones_traversees]
            ):
                console.print(ligne)
        else:  # 100 % hors profil — un titre sans ligne se lit comme un bug (DT-22)
            console.print(f"  {msg.analyse_repartition_vide()}")
        console.print()
        n_echantillons = int(result.parametres.get("n_echantillons_effectif", 0))
        console.print(msg.analyse_distorsion_titre(n_echantillons))
        seuil = float(result.parametres.get("distorsion_max_ppm", 0))
        for ligne in msg.analyse_bloc_distorsion(result.distorsions, seuil):
            console.print(ligne)
    console.print()
    famille_libelle = msg.FAMILLE_LIBELLE.get(famille_cible, msg.FAMILLE_LIBELLE_DEFAUT)
    ligne_reco = msg.analyse_recommandation(
        reco.action, reco.cible_libelle, reco.cible_epsg, famille_libelle
    )
    _ligne(console, ligne_reco, tete="→ ", glyphe="[cyan]→[/cyan] ")
    _ligne(console, msg.analyse_motif(reco.motif), tete="  ")
    # DT-26 : la marque porte sur ce qui BOUGE. Préservation → signe positif ;
    # changement de famille (repli CSRS, ≈ 1 m au Québec) → ⚠. Le glyphe et la
    # couleur se décident ici : `messages.py` reste sans balisage Rich.
    ligne_datum = msg.analyse_ligne_datum(result.famille, reco.cible_epsg, action=reco.action)
    marque = msg.marque_datum(result.famille, famille_cible)
    glyphe = "[green]✓[/green]" if marque == msg.MARQUE_DATUM_PRESERVE else "[yellow]⚠[/yellow]"
    # tête de 4 caractères : « ␣␣ » + glyphe + « ␣ » — seule sa LARGEUR compte,
    # le glyphe balisé la remplace sur la première ligne.
    _ligne(console, ligne_datum, tete="    ", glyphe=f"  {glyphe} ")
    note_datum = msg.analyse_note_datum(result.famille)
    if note_datum is not None:  # conseil neutre : ni ⚠, ni ✓
        _ligne(console, note_datum, tete="    ")
    for av in result.avertissements:
        _ligne(console, av, tete="  ⚠ ", glyphe="  [yellow]⚠[/yellow] ")
    alt_split = next((alt for alt in reco.alternatives if alt.get("action") == "split"), None)
    if alt_split is not None:
        console.print()
        n_sorties = len(alt_split.get("zones", []))
        _ligne(console, msg.analyse_ligne_alternative_split(n_sorties), tete="  ")
    console.print()
    if chemin_rapport is not None:
        _ligne(
            console,
            msg.analyse_rapport(chemin_rapport.name),
            tete="✓ ",
            glyphe="[green]✓[/green] ",
        )
    # N2 (DT-29) : `Pour appliquer : crszone apply <couche>` s'affichait DANS
    # `apply` lui-même — l'outil proposait la commande en cours. Elle ne
    # s'adresse qu'au lecteur d'une ANALYSE, et seulement s'il y a quelque
    # chose à appliquer (DT-22 : jamais quand `action == "aucune"`).
    if suggerer_apply and reco.action != "aucune":
        _ligne(console, msg.analyse_pour_appliquer(couche.name), tete="  ")


def mode_auto(console: Console, result: AnalysisResult) -> None:
    """Ligne « Mode --auto : … » entre le résumé abrégé et les sorties (CLI_UX §5)."""
    reco = result.recommandation
    console.print(msg.apply_mode_auto(reco.cible_libelle, reco.cible_epsg, action=reco.action))


def menu_options(console: Console, result: AnalysisResult) -> None:
    """Menu de décision interactif d'apply (CLI_UX §4)."""
    for ligne in msg.apply_menu(result):
        console.print(ligne)


def rappel_hors_seuil(console: Console, valeur_ppm: float) -> None:
    """Rappel affiché après le choix `[2]` si le fuseau dépasse le seuil (CLI_UX §4).

    `valeur_ppm` : la valeur qui franchit réellement le seuil (DT-03), pas forcément
    `max_ppm` — voir `messages.apply_hors_seuil`.
    """
    console.print(f"  [yellow]⚠[/yellow] {msg.apply_hors_seuil(valeur_ppm)}")


def succes_apply(console: Console, apply_result: ApplyResult) -> None:
    """Écran de succès d'apply (CLI_UX §4)."""
    vert = "[green]✓[/green] "
    for f in apply_result.fichiers:
        _ligne(
            console,
            msg.apply_ligne_sortie(f.chemin, f.epsg, f.n_entites),
            tete="✓ ",
            glyphe=vert,
        )
    _ligne(
        console,
        msg.apply_ligne_journal(apply_result.journal),
        tete="✓ ",
        glyphe=vert,
    )
    for pipeline in apply_result.pipeline_proj:
        _ligne(console, msg.apply_ligne_pipeline(pipeline))
    for av in apply_result.avertissements:
        _ligne(console, av, tete="  ⚠ ", glyphe="  [yellow]⚠[/yellow] ")
