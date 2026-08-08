"""Adaptateur CLI (Typer + Rich) : sous-commandes analyze / apply / grid.

Couche mince (ARCHITECTURE §2-§3) : composition + routage + présentation, aucune
logique métier. Traduit les exceptions typées du noyau en codes de sortie (SPEC
§10 / ARCHITECTURE §5). Point d'entrée console : crszone = crs_zone_toolkit.cli:app.
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import typer
from rich.console import Console

import crs_zone_toolkit
from crs_zone_toolkit import affichage
from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.errors import (
    CrsZoneError,
    EmptyLayerError,
    InvalidGeometryError,
    LayerReadError,
    MissingCrsError,
    NonInteractiveError,
    OutputExistsError,
    TransformUnavailableError,
    UnknownRegionError,
)
from crs_zone_toolkit.core.results import AnalysisResult, Decision

app = typer.Typer(add_completion=False, help=msg.CLI_AIDE, no_args_is_help=True)

out = Console()
err = Console(stderr=True)


def _forcer_utf8() -> None:
    """Force l'UTF-8 sur stdout/stderr (DT-15). Sans ça, une sortie redirigée sous
    Windows retombe sur cp1252 : le « → » de la recommandation (et de l'aide)
    plante (UnicodeEncodeError) et --json ressort en mojibake. Les flux de
    test/capture qui n'exposent pas ``reconfigure`` sont laissés intacts."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue
        with contextlib.suppress(ValueError, OSError):  # flux déjà engagé / non reconfigurable
            reconfigurer(encoding="utf-8")


# À l'import du module CLI (donc avant app()) : couvre --help, --version et
# l'invocation sans argument, dont la sortie est émise avant le callback _global.
_forcer_utf8()

# Mapping exceptions noyau → code de sortie (ARCHITECTURE §5). Défaut = 1.
_CODES: dict[type[CrsZoneError], int] = {
    MissingCrsError: 2,
    OutputExistsError: 2,
    NonInteractiveError: 2,
    EmptyLayerError: 1,
    InvalidGeometryError: 1,
    UnknownRegionError: 1,
    TransformUnavailableError: 1,
    LayerReadError: 1,
}


@contextmanager
def _codes_de_sortie() -> Iterator[None]:
    """Traduit toute CrsZoneError en message clair + code de sortie (SPEC §10)."""
    try:
        yield
    except CrsZoneError as exc:
        code = next((c for t, c in _CODES.items() if isinstance(exc, t)), 1)
        affichage.erreur(err, str(exc))
        raise typer.Exit(code) from exc


def _est_interactif() -> bool:
    """Vrai si stdin est un terminal (séam de test : monkeypatché en interactif)."""
    return sys.stdin.isatty()


def _version(valeur: bool) -> None:
    if valeur:
        out.print(f"crszone {crs_zone_toolkit.__version__}")
        raise typer.Exit()


class _Etat:
    def __init__(self, region: str) -> None:
        self.region = region


@app.callback()
def _global(
    ctx: typer.Context,
    region: str = typer.Option("qc", "--region", help=msg.CLI_AIDE_REGION),
    version: bool = typer.Option(
        False, "--version", callback=_version, is_eager=True, help="Afficher la version."
    ),
) -> None:
    _forcer_utf8()  # DT-15 : avant toute sortie, indépendamment du codepage console
    ctx.obj = _Etat(region=region)


@app.command(help=msg.CLI_AIDE_ANALYZE)
def analyze(
    ctx: typer.Context,
    couche: Path = typer.Argument(..., help="Couche vectorielle à analyser."),
    assume_crs: str | None = typer.Option(None, "--assume-crs", help="CRS supposé (EPSG:xxxx)."),
    report: Path | None = typer.Option(None, "--report", help="Dossier de sortie du rapport."),
    json_: bool = typer.Option(
        False,
        "--json",
        help=(
            "JSON seul sur stdout (résumé sur stderr)."
            " Sous PowerShell, préférez --json-out : la redirection > corrompt l'encodage."
        ),
    ),
    json_out: Path | None = typer.Option(
        None, "--json-out", help="Écrire le JSON dans un fichier."
    ),
    quiet: bool = typer.Option(False, "--quiet", help="Résumé réduit."),
) -> None:
    with _codes_de_sortie():
        from datetime import UTC, datetime

        from crs_zone_toolkit.core import report as _report
        from crs_zone_toolkit.core.targets import target_family

        region = ctx.obj.region
        layer, result, profile, grid = crs_zone_toolkit._charger_et_analyser(
            couche, region=region, assume_crs=assume_crs
        )
        quand = datetime.now(UTC)
        html = _report.render_html(
            result, layer, profile=profile, grid=grid, generated_at=quand, fichier=Path(couche).name
        )
        dossier = report if report is not None else Path(couche).parent
        chemin_rapport = _report._ecrire(
            html, Path(couche), out_dir=dossier, overwrite=True, generated_at=quand
        )

        humain = err if json_ else out
        if assume_crs is not None:
            affichage.bandeau_assume_crs(humain, assume_crs)
        if json_out is not None:
            Path(json_out).write_text(result.to_json(), encoding="utf-8")
        if json_:
            sys.stdout.write(result.to_json() + "\n")
        affichage.resume_analyse(
            humain,
            result,
            chemin_rapport,
            couche=Path(couche),
            n_entites=len(layer),
            profile=profile,
            crs_geographique=bool(layer.crs is not None and layer.crs.is_geographic),
            famille_cible=target_family(result.famille),
            abrege=quiet,
        )


def _resoudre_decision(
    result: AnalysisResult,
    *,
    choix: str | None,
    zone: int | None,
    auto: bool,
    humain: Console,
) -> Decision | None:
    """Route options → Decision (aucune logique métier ; renvoie None = annulation)."""
    dominant = result.zones_traversees[0].zone if result.zones_traversees else None
    if auto:
        return Decision("recommendation", "auto")
    if choix is not None:
        if choix == "zone":
            cible_zone = zone if zone is not None else dominant
            if cible_zone is None:
                raise typer.BadParameter(msg.zone_absente())
            return Decision("zone", "choice", zone=cible_zone)
        if choix in ("recommendation", "lambert", "split"):
            return Decision(choix, "choice")
        raise typer.BadParameter(msg.choix_invalide(choix))
    if not _est_interactif():
        raise NonInteractiveError(msg.NON_INTERACTIF)
    return _menu_interactif(result, humain)  # Task 8


def _menu_interactif(result: AnalysisResult, humain: Console) -> Decision | None:
    """Menu de décision interactif (CLI_UX §4). Renvoie None si annulation [0]."""
    affichage.menu_options(humain, result)
    choix = typer.prompt(msg.APPLY_INVITE, default="1")
    if choix == "0":
        return None
    if choix == "3":
        return Decision("split", "interactive")
    if choix == "2":
        dominant = result.zones_traversees[0].zone if result.zones_traversees else 1
        fuseau = typer.prompt(msg.APPLY_INVITE_FUSEAU, default=str(dominant), type=int)
        _rappel_si_hors_seuil(result, fuseau, humain)
        return Decision("zone", "interactive", zone=fuseau)
    return Decision("recommendation", "interactive")  # [1] ou entrée vide (défaut)


def _rappel_si_hors_seuil(result: AnalysisResult, fuseau: int, humain: Console) -> None:
    """Affiche `⚠ hors seuil` (CLI_UX §4) si la distorsion mesurée du fuseau choisi la dépasse.

    La distorsion n'est mesurée (analysis.py) que pour le fuseau dominant : si le
    fuseau choisi diffère, aucune donnée n'est disponible ici et on n'affiche rien
    (affichage informatif seulement, ne bloque jamais la décision consciente de
    l'utilisateur ; journalisée par ailleurs comme « choix contre recommandation »).

    La valeur affichée est celle qui FRANCHIT réellement le seuil : `min_ppm` ou
    `max_ppm`, la plus grande en valeur absolue (DT-03), pas systématiquement
    `max_ppm`, qui peut être à tort le côté qui ne dépasse pas.
    """
    if not result.zones_traversees or result.zones_traversees[0].zone != fuseau:
        return
    if not result.distorsions:
        return
    dominante = result.distorsions[0]
    seuil = result.parametres.get("distorsion_max_ppm")
    if seuil is None:
        return
    valeur = (
        dominante.max_ppm if abs(dominante.max_ppm) >= abs(dominante.min_ppm) else dominante.min_ppm
    )
    if abs(valeur) > float(seuil):
        affichage.rappel_hors_seuil(humain, valeur)


@app.command(help=msg.CLI_AIDE_APPLY)
def apply(
    ctx: typer.Context,
    couche: Path = typer.Argument(..., help="Couche vectorielle."),
    choix: str | None = typer.Option(None, "--choice", help="recommendation|zone|lambert|split."),
    zone: int | None = typer.Option(
        None, "--zone", help="Fuseau pour --choice zone (défaut : dominant)."
    ),
    auto: bool = typer.Option(False, "--auto", help="Appliquer la recommandation sans invite."),
    out_dir: Path | None = typer.Option(None, "--out", help="Dossier de sortie."),
    out_format: str = typer.Option("gpkg", "--format", help="gpkg | geojson | shp."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Écraser les sorties existantes."),
    assume_crs: str | None = typer.Option(None, "--assume-crs", help="CRS supposé (EPSG:xxxx)."),
    json_: bool = typer.Option(
        False,
        "--json",
        help=(
            "JSON du résultat sur stdout."
            " Sous PowerShell, préférez --json-out : la redirection > corrompt l'encodage."
        ),
    ),
    json_out: Path | None = typer.Option(
        None, "--json-out", help="Écrire le JSON dans un fichier."
    ),
) -> None:
    with _codes_de_sortie():
        # DT-19 : import paresseux (voie b, le brief l'autorise nommément) : un
        # import module-level de core.apply charge geopandas/pyproj/shapely dès
        # `crszone --help`, mesuré ~0,7 s contre ~0,07 s ; le texte d'aide reste
        # littéral, verrouillé par test_aide_apply_couvre_formats_sortie.
        from crs_zone_toolkit.core.apply import FORMATS_SORTIE

        if out_format not in FORMATS_SORTIE:
            raise typer.BadParameter(msg.format_invalide(out_format, FORMATS_SORTIE))

        from crs_zone_toolkit.core import apply as _core_apply
        from crs_zone_toolkit.core.targets import target_family

        region = ctx.obj.region
        layer, result, profile, grid = crs_zone_toolkit._charger_et_analyser(
            couche, region=region, assume_crs=assume_crs
        )
        humain = err if json_ else out
        # validation --zone
        zones_connues = {int(z.zone) for z in result.zones_traversees} | {
            int(f.zone) for f in profile.fuseaux
        }
        if choix == "zone" and zone is not None and zone not in zones_connues:
            raise typer.BadParameter(msg.zone_invalide(zone))

        cible = Path(out_dir) if out_dir is not None else Path(couche).parent

        # DT-23 : le menu promet « [0] Annuler (relire le rapport avant de décider) ».
        # La promesse n'a de sens que si le rapport existe QUAND le menu s'affiche :
        # il est donc écrit ici, avant le résumé et avant la décision.
        #
        # Périmètre arbitré (protocole §9, N14) : mode interactif et `--choice split`,
        # où six fichiers sortent d'une seule décision. `--auto` n'ouvre aucun menu et
        # ne promet rien ; les autres `--choice` non plus. `_est_interactif()` est
        # consulté pour ne rien écrire sur le chemin qui va lever NonInteractiveError.
        mode_interactif = not auto and choix is None
        ecrire_rapport = choix == "split" or (mode_interactif and _est_interactif())
        chemin_rapport = None
        if ecrire_rapport:
            from datetime import UTC, datetime

            from crs_zone_toolkit.core import report as _report

            quand = datetime.now(UTC)
            html = _report.render_html(
                result,
                layer,
                profile=profile,
                grid=grid,
                generated_at=quand,
                fichier=Path(couche).name,
            )
            chemin_rapport = _report._ecrire(
                html, Path(couche), out_dir=cible, overwrite=True, generated_at=quand
            )

        # DT-20 n°5 : SPEC §5.2, apply « exécute l'analyse et affiche le résumé » avant
        # la décision. `chemin_rapport` vaut None hors du périmètre ci-dessus, et
        # `affichage.resume_analyse` omet alors la ligne « Rapport détaillé ».
        affichage.resume_analyse(
            humain,
            result,
            chemin_rapport,
            couche=Path(couche),
            n_entites=len(layer),
            profile=profile,
            crs_geographique=bool(layer.crs is not None and layer.crs.is_geographic),
            famille_cible=target_family(result.famille),
            abrege=bool(auto or choix is not None),
            # N2 (DT-29) : proposer « crszone apply » DANS apply est une absurdité.
            suggerer_apply=False,
        )

        if auto:  # CLI_UX §5 : le mode automatique s'annonce (DT-27, observation N4)
            affichage.mode_auto(humain, result)

        decision = _resoudre_decision(result, choix=choix, zone=zone, auto=auto, humain=humain)
        if decision is None:  # annulation interactive [0]
            affichage.message(humain, msg.apply_annule(chemin_rapport))
            return

        apply_result = _core_apply.apply(
            layer,
            Path(couche).stem,
            result,
            decision,
            profile=profile,
            grid=grid,
            out_dir=cible,
            out_format=out_format,
            overwrite=overwrite,
        )
        if json_out is not None:
            Path(json_out).write_text(apply_result.to_json(), encoding="utf-8")
        if json_:
            sys.stdout.write(apply_result.to_json() + "\n")
        affichage.succes_apply(humain, apply_result)


@app.command(help=msg.CLI_AIDE_GRID)
def grid(
    ctx: typer.Context,
    out_path: Path | None = typer.Option(None, "--out", help="Chemin du fichier de grille."),
    out_format: str = typer.Option("geojson", "--format", help="geojson | gpkg."),
    no_clip: bool = typer.Option(False, "--no-clip", help="Bandes complètes, non découpées."),
) -> None:
    with _codes_de_sortie():
        # DT-19 : le texte d'aide reste littéral (voie b), verrouillé par
        # test_aide_grid_couvre_formats_grille : `crs_zone_toolkit.FORMATS_GRILLE`
        # est un attribut déjà chargé (pas d'import lourd), donc pas de coût ici.
        if out_format not in crs_zone_toolkit.FORMATS_GRILLE:
            raise typer.BadParameter(
                msg.format_invalide(out_format, crs_zone_toolkit.FORMATS_GRILLE)
            )

        region = ctx.obj.region
        # DT-19 : l'extension de sortie EST le nom du format, par construction de
        # _FORMATS_GRILLE (geojson/gpkg), pas de correspondance à maintenir à part.
        ext = out_format
        cible = out_path if out_path is not None else Path(f"grille_mtm_{region}.{ext}")
        chemin, n, attributs = crs_zone_toolkit._generer_grille(
            region=region, out=cible, out_format=out_format, clip=not no_clip
        )
        affichage.resume_grille(out, chemin, n, attributs, clip=not no_clip)
