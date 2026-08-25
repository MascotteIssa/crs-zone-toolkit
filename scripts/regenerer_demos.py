"""Régénère les ressources de démonstration du README (DT-17).

À lancer après toute modification du gabarit du rapport (`templates/rapport.html.j2`),
de la règle de décision (`core/analysis._decide`) ou du résumé terminal
(`affichage.resume_analyse` / `core/messages.py`) — sans quoi les captures du README
montreraient un outil qui n'existe plus.

Usage :
    uv run python scripts/regenerer_demos.py --quoi tout
    uv run python scripts/regenerer_demos.py --quoi exemple
    uv run python scripts/regenerer_demos.py --quoi captures
    uv run python scripts/regenerer_demos.py --quoi gif

Prérequis :
    - une couche de démonstration réelle (voir --couche ; par défaut la couche
      utilisée en J7, `tests/user_test/data/bdat/regio_s.shp` — non versionnée,
      `tests/user_test/` est gitignoré : fournissez la vôtre si vous ne l'avez
      pas, p. ex. les « Découpages administratifs » de Données Québec) ;
    - `playwright` et `Pillow`, hors dépendances du paquet (outil de mainteneur,
      cf. l'historique du projet, entrée du 2026-07-25) : `uv pip install playwright
      pillow` puis, si nécessaire, `playwright install chromium` (déjà en cache
      sur ce poste — ne relancez cette commande que si le lancement du
      navigateur échoue avec « Executable doesn't exist »).

Contrainte de vérité (DT-17) : chaque ressource est produite depuis le moteur
réel (`crs_zone_toolkit._charger_et_analyser` puis `core.report` /
`affichage.resume_analyse`), jamais depuis un HTML recopié ou un gabarit dupliqué.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from datetime import UTC, datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"
IMAGES = DOCS / "images"
EXEMPLE_RAPPORT = DOCS / "exemple_rapport.html"
GIF = IMAGES / "demo.gif"
README = RACINE / "README.md"
PAGE_INTERFACE = RACINE / "src" / "crs_zone_toolkit" / "gui" / "web" / "index.html"
COUCHE_DEFAUT = RACINE / "tests" / "user_test" / "data" / "bdat" / "regio_s.shp"
REGION_DEFAUT = "qc"


def _forcer_utf8() -> None:
    """Force l'UTF-8 sur stdout/stderr (même correctif que `cli.py` et
    `publier_release.py`, DT-15). Sans ça, une console Windows non redirigée
    en UTF-8 retombe sur cp1252 : un futur caractère hors de ce jeu (« ✓ »,
    « → », …) planterait (UnicodeEncodeError) sans prévenir. Ce script
    n'imprime aujourd'hui aucun caractère de ce genre — fermeture préventive
    de la famille DT-15 (décision du 2026-08-02), pas une réparation. Les
    flux de test/capture qui n'exposent pas ``reconfigure`` sont laissés
    intacts."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue
        with contextlib.suppress(ValueError, OSError):  # flux déjà engagé / non reconfigurable
            reconfigurer(encoding="utf-8")


# Paramètres connus des ressources d'origine (journal 2026-07-25) : console Rich
# en mode enregistrement, largeur 92, truecolor ; GIF 860×740.
LARGEUR_CONSOLE = 92
TAILLE_GIF = (860, 740)

# Largeur de la console pour l'extrait README (Phase C, tâche 4) : 99 caractères
# est la largeur du filet horizontal (`Rule`) déjà présent dans le README —
# empiriquement, un `Console(width=99)` produit un filet de 99 caractères
# (vérifié : `width=100` en produit un de 100). À ne pas confondre avec
# `LARGEUR_CONSOLE` ci-dessus (92), propre au GIF.
LARGEUR_EXTRAIT = 99

# Marqueurs HTML (invisibles au rendu GitHub/PyPI) qui bornent le bloc de code
# de la section « En trente secondes » du README (Phase C, tâche 4, DT-17).
MARQUEUR_EXTRAIT_DEBUT = "<!-- extrait:debut -->"
MARQUEUR_EXTRAIT_FIN = "<!-- extrait:fin -->"

# Second bloc console du README (`crszone apply … --auto`), hors des marqueurs
# ci-dessus donc longtemps hors outillage : c'est précisément celui qui est
# parti périmé deux fois (clôture Phase C, puis passe corrective du 01/08).
# Un bloc périmé PAR SOUSTRACTION ne contient pas les marqueurs de ce qui lui
# manque — aucune recherche textuelle ne pouvait le rattraper (DT-17).
MARQUEUR_APPLY_DEBUT = "<!-- apply:debut -->"
MARQUEUR_APPLY_FIN = "<!-- apply:fin -->"

# Le bloc `apply` illustre le cas SIMPLE (une couche d'un seul fuseau), là où
# l'extrait « En trente secondes » montre la province entière. Deux couches
# différentes, donc, et deux propos différents.
COUCHE_APPLY = RACINE / "tests" / "user_test" / "data" / "montreal.gpkg"

# Horodatage figé (jamais `datetime.now`) pour le nom du rapport HTML affiché
# dans l'extrait : l'extrait doit être identique d'une régénération à l'autre
# (idempotence, brief §Step 2) — ce rapport est de toute façon écrit dans un
# dossier temporaire, jamais dans docs/.
HORODATAGE_EXTRAIT = datetime(2026, 7, 28, 13, 8, 42, tzinfo=UTC)

# Même raison pour `docs/exemple_rapport.html` (2026-08-01, DT-17) : avec
# `datetime.now`, CHAQUE régénération produisait un diff — sur le rapport, et
# par ricochet sur les quatre captures, qui le photographient horodatage
# compris. Impossible, dans ces conditions, de tenir l'objectif inscrit à
# DT-17 : « un job CI qui échoue si les ressources dérivent ». Contrepartie
# assumée : la date affichée sur l'exemple est celle du gel, pas celle de la
# dernière régénération.
HORODATAGE_EXEMPLE = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)


def _erreur_couche_absente(couche: Path) -> None:
    raise SystemExit(
        f"Couche de démonstration introuvable : {couche}\n"
        "Aucune ressource n'a été modifiée. `tests/user_test/` est gitignoré "
        "(données réelles de test manuel, non distribuées) : fournissez la "
        "vôtre via --couche <chemin vers gpkg/shp/geojson>, ou obtenez la "
        "couche de référence (« Découpages administratifs », Données Québec, "
        "CC-BY 4.0 — voir docs/DATA_REFERENCE.md §6.2)."
    )


def _analyser(couche: Path, *, region: str) -> tuple:
    """Charge et analyse la couche via le moteur réel (composition partagée)."""
    if not couche.is_file():
        _erreur_couche_absente(couche)
    from crs_zone_toolkit import _charger_et_analyser

    return _charger_et_analyser(couche, region=region)


def regenerer_exemple_rapport(
    couche: Path = COUCHE_DEFAUT,
    *,
    region: str = REGION_DEFAUT,
    sortie: Path = EXEMPLE_RAPPORT,
) -> Path:
    """Régénère `docs/exemple_rapport.html` depuis le moteur réel (jamais recopié)."""
    from crs_zone_toolkit.core import report as _report

    layer, result, profile, grid = _analyser(couche, region=region)
    html = _report.render_html(
        result,
        layer,
        profile=profile,
        grid=grid,
        generated_at=HORODATAGE_EXEMPLE,
        fichier=couche.name,
    )
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(html, encoding="utf-8")
    return sortie


def regenerer_extrait(
    couche: Path = COUCHE_DEFAUT,
    *,
    region: str = REGION_DEFAUT,
    readme: Path = README,
) -> Path:
    """Régénère l'extrait terminal « En trente secondes » du README (DT-17).

    Même mécanisme que `regenerer_gif` (ci-dessous) : une console Rich à
    largeur fixe reçoit la sortie du VRAI code d'affichage
    (`affichage.resume_analyse`), jamais un texte recopié à la main — mais ici
    sans couleur (`no_color=True`), car l'extrait README est un bloc de texte
    brut (```console), pas un GIF. Le rapport HTML généré au passage n'est
    écrit que dans un dossier temporaire : seul son nom de fichier apparaît
    dans le texte capturé (ligne « Rapport détaillé »).

    Échoue bruyamment (aucun fichier modifié) si les marqueurs sont absents du
    README ou si la couche de démonstration manque (via `_analyser`).
    """
    import tempfile

    from rich.console import Console as RichConsole

    from crs_zone_toolkit import affichage
    from crs_zone_toolkit.core import report as _report
    from crs_zone_toolkit.core.targets import target_family

    if not readme.is_file():
        raise SystemExit(f"{readme} introuvable — aucun extrait n'a été modifié.")
    texte = readme.read_text(encoding="utf-8")
    if MARQUEUR_EXTRAIT_DEBUT not in texte or MARQUEUR_EXTRAIT_FIN not in texte:
        raise SystemExit(
            f"Marqueurs {MARQUEUR_EXTRAIT_DEBUT!r}/{MARQUEUR_EXTRAIT_FIN!r} introuvables dans "
            f"{readme} — aucun extrait n'a été modifié."
        )

    layer, result, profile, grid = _analyser(couche, region=region)

    tampon = io.StringIO()
    rec = RichConsole(width=LARGEUR_EXTRAIT, no_color=True, file=tampon)
    rec.print(f"[green]$[/green] crszone --region {region} analyze {couche.name}")

    with tempfile.TemporaryDirectory() as tmp:
        html = _report.render_html(
            result,
            layer,
            profile=profile,
            grid=grid,
            generated_at=HORODATAGE_EXTRAIT,
            fichier=couche.name,
        )
        chemin_rapport = _report._ecrire(
            html, couche, out_dir=Path(tmp), overwrite=True, generated_at=HORODATAGE_EXTRAIT
        )
        affichage.resume_analyse(
            rec,
            result,
            chemin_rapport,
            couche=couche,
            n_entites=len(layer),
            profile=profile,
            crs_geographique=bool(layer.crs is not None and layer.crs.is_geographic),
            famille_cible=target_family(result.famille),
        )

    return _remplacer_bloc(
        readme,
        MARQUEUR_EXTRAIT_DEBUT,
        MARQUEUR_EXTRAIT_FIN,
        _rstrip_lignes(tampon.getvalue()),
    )


def _remplacer_bloc(readme: Path, debut: str, fin: str, contenu: str) -> Path:
    """Remplace le bloc borné par `debut`/`fin` dans le README. Échoue bruyamment."""
    if not readme.is_file():
        raise SystemExit(f"{readme} introuvable — aucun bloc n'a été modifié.")
    texte = readme.read_text(encoding="utf-8")
    if debut not in texte or fin not in texte:
        raise SystemExit(
            f"Marqueurs {debut!r}/{fin!r} introuvables dans {readme} — aucun bloc modifié."
        )
    avant, reste = texte.split(debut, 1)
    _, apres = reste.split(fin, 1)
    bloc = f"{debut}\n```console\n{contenu}\n```\n{fin}"
    readme.write_text(f"{avant}{bloc}{apres}", encoding="utf-8")
    return readme


def _rstrip_lignes(texte: str) -> str:
    """Rich laisse une espace de fin sur les lignes coupées ; le hook pre-commit
    `trailing-whitespace` couvre README.md."""
    return "\n".join(ligne.rstrip() for ligne in texte.splitlines())


def regenerer_bloc_apply(
    couche: Path = COUCHE_APPLY,
    *,
    region: str = REGION_DEFAUT,
    readme: Path = README,
) -> Path:
    """Régénère le bloc `crszone apply … --auto` du README (DT-17).

    Rejoue le VRAI enchaînement de la commande — résumé abrégé, ligne de mode
    automatique (DT-27), écriture, écran de succès — dans un dossier temporaire,
    en s'y plaçant pour que les chemins affichés restent relatifs (`sorties\\…`)
    comme un lecteur les verrait.
    """
    import os
    import tempfile

    from rich.console import Console as RichConsole

    from crs_zone_toolkit import affichage
    from crs_zone_toolkit.core import apply as _apply
    from crs_zone_toolkit.core.results import Decision
    from crs_zone_toolkit.core.targets import target_family

    layer, result, profile, grid = _analyser(couche, region=region)

    tampon = io.StringIO()
    rec = RichConsole(width=LARGEUR_EXTRAIT, no_color=True, file=tampon)
    rec.print(f"[green]$[/green] crszone apply {couche.name} --out sorties --auto")

    ancien = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.chdir(tmp)
            affichage.resume_analyse(
                rec,
                result,
                None,
                couche=couche,
                n_entites=len(layer),
                profile=profile,
                crs_geographique=bool(layer.crs is not None and layer.crs.is_geographic),
                famille_cible=target_family(result.famille),
                abrege=True,
                suggerer_apply=False,
            )
            affichage.mode_auto(rec, result)
            produit = _apply.apply(
                layer,
                couche.stem,
                result,
                Decision("recommendation", "auto"),
                profile=profile,
                grid=grid,
                out_dir=Path("sorties"),
            )
            affichage.succes_apply(rec, produit)
        finally:
            os.chdir(ancien)

    return _remplacer_bloc(
        readme, MARQUEUR_APPLY_DEBUT, MARQUEUR_APPLY_FIN, _rstrip_lignes(tampon.getvalue())
    )


def regenerer_captures(
    rapport_html: Path = EXEMPLE_RAPPORT,
    *,
    sortie_dir: Path = IMAGES,
    timeout_ms: int = 30_000,
) -> list[Path]:
    """Captures Playwright du rapport, deux thèmes + section distorsion (CLI_UX/SPEC §7).

    Le rapport doit déjà exister (régénéré depuis le moteur réel par
    `regenerer_exemple_rapport` — cette fonction ne fait AUCUN calcul, elle
    photographie ce qui a été rendu).
    """
    if not rapport_html.is_file():
        raise SystemExit(
            f"{rapport_html} introuvable — lancez d'abord "
            "`--quoi exemple` (aucune capture n'a été modifiée)."
        )
    from playwright.sync_api import sync_playwright

    sortie_dir.mkdir(parents=True, exist_ok=True)
    url = rapport_html.resolve().as_uri()
    produits: list[Path] = []

    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True, timeout=timeout_ms)
        try:
            for theme, suffixe in (("light", "clair"), ("dark", "sombre")):
                contexte = navigateur.new_context(
                    viewport={"width": 1280, "height": 900},
                    device_scale_factor=2,
                    color_scheme=theme,
                )
                page = contexte.new_page()
                page.goto(url, timeout=timeout_ms)
                page.wait_for_load_state("networkidle", timeout=timeout_ms)

                cible = sortie_dir / f"rapport-{suffixe}.png"
                page.screenshot(path=str(cible))
                produits.append(cible)

                # Section « 03 Distorsion mesurée » — élément signature (pas d'id
                # dédié dans le gabarit ; on borne le rectangle par les bounding
                # boxes du titre et de la légende, sans modifier src/).
                titre = page.get_by_role("heading", name="Distorsion mesurée")
                titre.scroll_into_view_if_needed(timeout=timeout_ms)
                section = titre.locator("xpath=..")
                legende = page.locator(".d-legend")
                box_titre = section.bounding_box()
                box_legende = legende.bounding_box()
                if box_titre is None or box_legende is None:
                    raise SystemExit(
                        "Section « Distorsion mesurée » introuvable dans le rapport "
                        f"({rapport_html}) — gabarit modifié ? Aucune capture "
                        "de distorsion écrite."
                    )
                pad = 16
                x = min(box_titre["x"], box_legende["x"])
                largeur = (
                    max(
                        box_titre["x"] + box_titre["width"], box_legende["x"] + box_legende["width"]
                    )
                    - x
                )
                clip = {
                    "x": x,
                    "y": box_titre["y"] - pad,
                    "width": largeur,
                    "height": (box_legende["y"] + box_legende["height"]) - box_titre["y"] + 2 * pad,
                }
                cible_d = sortie_dir / f"rapport-distorsion-{suffixe}.png"
                page.screenshot(path=str(cible_d), clip=clip)
                produits.append(cible_d)
                contexte.close()
        finally:
            navigateur.close()
    return produits


def regenerer_captures_interface(
    couche: Path = COUCHE_DEFAUT,
    *,
    region: str = REGION_DEFAUT,
    page_html: Path = PAGE_INTERFACE,
    sortie_dir: Path = IMAGES,
    timeout_ms: int = 30_000,
) -> list[Path]:
    """Captures de l'écran de recommandation de l'interface, deux thèmes.

    Même exigence que pour le rapport : la page photographiée est **celle que
    l'application charge** (`gui/web/index.html`), peuplée par les **vrais
    chiffres du moteur**. Rien n'est simulé sauf le pont `pywebview.api`, que
    seule une fenêtre native peut fournir : on lui substitue un objet qui rend
    exactement ce que rendrait `gui.service`, puis on suit le parcours réel de
    l'écran (choisir un fichier, lancer l'analyse).

    Le rendu n'a pas de cadre de fenêtre du système, et n'en a pas besoin : la
    barre de titre visible appartient à la page elle-même.
    """
    if not page_html.is_file():  # pragma: no cover — déplacement de la page
        raise SystemExit(f"{page_html} introuvable — aucune capture écrite.")
    _, resultat, _, _ = _analyser(couche, region=region)

    import json

    from playwright.sync_api import sync_playwright

    analyse = json.dumps(resultat.to_dict(), ensure_ascii=False)
    pont = (
        "window.pywebview = { api: {"
        f"  analyze: async () => ({{ analysis: {analyse},"
        "    report_path: 'C:/sorties/exemple_analyse_crs.html' }),"
        "  pick_file: async () => 'C:/donnees/regio_s.shp',"
        "  pick_folder: async () => 'C:/sorties',"
        "  open_path: async () => null"
        "} };"
    )

    sortie_dir.mkdir(parents=True, exist_ok=True)
    url = page_html.resolve().as_uri()
    produits: list[Path] = []

    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True, timeout=timeout_ms)
        try:
            for theme, suffixe in (("light", "clair"), ("dark", "sombre")):
                contexte = navigateur.new_context(
                    viewport={"width": 960, "height": 720},
                    device_scale_factor=2,
                    color_scheme=theme,
                )
                page = contexte.new_page()
                page.add_init_script(pont)
                page.goto(url, timeout=timeout_ms)
                page.click("[data-goto='fichier']", timeout=timeout_ms)
                page.click("#browse", timeout=timeout_ms)
                page.click("#btnAnalyser", timeout=timeout_ms)
                page.wait_for_selector("section[data-screen='resultat'].active", timeout=timeout_ms)
                page.wait_for_timeout(400)  # transition d'écran

                cible = sortie_dir / f"interface-{suffixe}.png"
                page.screenshot(path=str(cible))
                produits.append(cible)
                contexte.close()
        finally:
            navigateur.close()
    return produits


def _fenetre_html(code: str, foreground: str, background: str, *, titre: str) -> str:
    """Décor de fenêtre de terminal autour d'un fragment HTML déjà rendu par Rich.

    `code` est le fragment `<span>` déjà résolu (couleurs réelles, pas un
    gabarit) : un seul passage de f-string, aucun second `.format()` — Rich
    aurait sinon buté sur les accolades de la feuille de style CSS ci-dessous.
    Contenu bas-aligné et débordement masqué : une fenêtre de hauteur fixe qui,
    au fil des captures successives, « défile » comme un vrai terminal — sans
    calcul de recadrage côté Pillow.
    """
    largeur, hauteur = TAILLE_GIF
    barre_h = 34
    corps_h = hauteur - barre_h
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; }}
body {{ font-family: Menlo, 'DejaVu Sans Mono', Consolas, 'Courier New', monospace; }}
.fenetre {{ width:{largeur}px; height:{hauteur}px; background:{background}; overflow:hidden; }}
.barre {{ height:{barre_h}px; background:#3a3a3a; display:flex; align-items:center;
  gap:7px; padding:0 14px; }}
.pt {{ width:11px; height:11px; border-radius:50%; }}
.p1{{background:#ff5f57}} .p2{{background:#febc2e}} .p3{{background:#28c840}}
.titre {{ margin-left:8px; color:#bdbdbd; font-size:12px; }}
.corps {{ height:{corps_h}px; padding:16px 20px; color:{foreground}; font-size:13px;
  line-height:18px; overflow:hidden; display:flex; flex-direction:column;
  justify-content:flex-end; }}
.corps code {{ display:block; white-space:pre; font-family:inherit; }}
</style></head><body>
<div class="fenetre">
  <div class="barre">
    <span class="pt p1"></span><span class="pt p2"></span><span class="pt p3"></span>
    <span class="titre">{titre}</span>
  </div>
  <div class="corps"><code>{code}</code></div>
</div>
</body></html>"""


def regenerer_gif(
    couche: Path = COUCHE_DEFAUT,
    *,
    region: str = REGION_DEFAUT,
    sortie: Path = GIF,
    timeout_ms: int = 45_000,
) -> Path:
    """Régénère `docs/images/demo.gif` depuis le vrai code d'affichage (DT-17).

    Méthode (journal 2026-07-25) : les `Console` de `cli.py` sont remplacées par
    une console Rich en mode enregistrement (truecolor, largeur 92) — le VRAI
    code d'affichage (`affichage.resume_analyse`) produit la sortie ; chaque
    appel `print()` est intercepté pour capturer un instantané HTML cumulatif
    (`export_html`), ce qui donne naturellement une frame par ligne réellement
    affichée (pas de rejeu inventé). Le décor de fenêtre est ajouté autour, les
    frames sont capturées par Playwright et assemblées avec Pillow.
    """
    import tempfile

    from PIL import Image
    from playwright.sync_api import sync_playwright
    from rich.console import Console as RichConsole
    from rich.terminal_theme import MONOKAI

    from crs_zone_toolkit import affichage
    from crs_zone_toolkit.core import report as _report
    from crs_zone_toolkit.core.targets import target_family

    layer, result, profile, grid = _analyser(couche, region=region)

    # `file=io.StringIO()` : la console n'écrit jamais dans le vrai terminal —
    # sous Windows, l'écriture réelle passe par le rendu « legacy console »
    # (cp1252) et plante sur les accents ; seul l'enregistrement (`record=True`,
    # `export_html`) nous intéresse ici.
    rec = RichConsole(
        record=True,
        force_terminal=True,
        color_system="truecolor",
        width=LARGEUR_CONSOLE,
        file=io.StringIO(),
    )
    frames_html: list[str] = []
    _imprimer_original = rec.print
    fg_hex = MONOKAI.foreground_color.hex
    bg_hex = MONOKAI.background_color.hex

    def _imprimer_et_capturer(*args: object, **kwargs: object) -> None:
        _imprimer_original(*args, **kwargs)
        # code_format="{code}" : fragment brut (couleurs déjà résolues par Rich),
        # pas de gabarit à re-`.format()` — voir la docstring de `_fenetre_html`.
        fragment = rec.export_html(
            theme=MONOKAI, inline_styles=True, clear=False, code_format="{code}"
        )
        frames_html.append(_fenetre_html(fragment, fg_hex, bg_hex, titre="crszone — terminal"))

    rec.print = _imprimer_et_capturer  # type: ignore[method-assign]

    rec.print(f"[green]$[/green] crszone --region {region} analyze {couche.name}")

    with tempfile.TemporaryDirectory() as tmp:
        quand = datetime.now(UTC)
        html = _report.render_html(
            result, layer, profile=profile, grid=grid, generated_at=quand, fichier=couche.name
        )
        chemin_rapport = _report._ecrire(
            html, couche, out_dir=Path(tmp), overwrite=True, generated_at=quand
        )
        affichage.resume_analyse(
            rec,
            result,
            chemin_rapport,
            couche=couche,
            n_entites=len(layer),
            profile=profile,
            crs_geographique=bool(layer.crs is not None and layer.crs.is_geographic),
            famille_cible=target_family(result.famille),
        )

    if not frames_html:
        raise SystemExit("Aucune frame capturée — le résumé terminal n'a rien affiché.")

    # Pauses : une frame dupliquée sur la commande (avant « exécution ») et
    # deux sur le résultat final (avant bouclage du GIF) — vise ~8,7 s au total
    # (paramètre connu de la ressource d'origine, journal 2026-07-25).
    sequence = [frames_html[0]] + frames_html + [frames_html[-1]] * 2
    durees = [500] + [150] * len(frames_html) + [1400] * 2

    largeur, hauteur = TAILLE_GIF
    images: list[Image.Image] = []
    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True, timeout=timeout_ms)
        try:
            page = navigateur.new_page(viewport={"width": largeur, "height": hauteur})
            for doc in sequence:
                page.set_content(doc, timeout=timeout_ms)
                png = page.screenshot(timeout=timeout_ms)
                images.append(Image.open(io.BytesIO(png)).convert("RGB"))
        finally:
            navigateur.close()

    sortie.parent.mkdir(parents=True, exist_ok=True)
    premiere, reste = images[0], images[1:]
    premiere.save(
        sortie,
        save_all=True,
        append_images=reste,
        duration=durees,
        loop=0,
        optimize=False,
    )
    total_s = sum(durees) / 1000
    print(f"GIF écrit : {sortie} ({largeur}x{hauteur}, {len(images)} images, {total_s:.1f} s)")
    return sortie


def main(argv: list[str] | None = None) -> int:
    _forcer_utf8()  # DT-15 : avant toute sortie, indépendamment du codepage console
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--quoi",
        choices=("apply", "captures", "exemple", "extrait", "gif", "interface", "tout"),
        default="tout",
        help="Ressource(s) à régénérer.",
    )
    parser.add_argument(
        "--couche",
        type=Path,
        default=COUCHE_DEFAUT,
        help=f"Couche de démonstration (défaut : {COUCHE_DEFAUT}).",
    )
    parser.add_argument("--region", default=REGION_DEFAUT, help="Profil de région (défaut : qc).")
    args = parser.parse_args(argv)

    quoi = args.quoi
    if quoi in ("extrait", "tout"):
        chemin_extrait = regenerer_extrait(args.couche, region=args.region)
        print(f"Extrait README régénéré : {chemin_extrait}")
    if quoi in ("apply", "tout"):
        chemin_apply = regenerer_bloc_apply(region=args.region)
        print(f"Bloc apply du README régénéré : {chemin_apply}")
    if quoi in ("exemple", "tout"):
        chemin = regenerer_exemple_rapport(args.couche, region=args.region)
        print(f"Rapport d'exemple écrit : {chemin}")
    if quoi in ("captures", "tout"):
        produits = regenerer_captures()
        for p in produits:
            print(f"Capture écrite : {p}")
    if quoi in ("interface", "tout"):
        for chemin_interface in regenerer_captures_interface(args.couche, region=args.region):
            print(f"Capture d'interface écrite : {chemin_interface}")
    if quoi in ("gif", "tout"):
        regenerer_gif(args.couche, region=args.region)
    return 0


if __name__ == "__main__":
    sys.exit(main())
