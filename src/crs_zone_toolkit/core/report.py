"""Adaptateur sortant : rapport HTML auto-porté (Jinja2 + carte matplotlib) et sortie JSON.

Contrats : docs/SPEC.md §7-§8, gabarit visuel interne
(→ templates/rapport.html.j2). Aucune logique de recommandation ici
(docs/ARCHITECTURE.md §2). JSON : schema_version obligatoire (TP-33).
"""

from __future__ import annotations

import base64
import io
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
from jinja2 import Environment, PackageLoader
from markupsafe import Markup
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from crs_zone_toolkit.core import messages as msg
from crs_zone_toolkit.core.errors import OutputExistsError
from crs_zone_toolkit.core.profile import RegionProfile
from crs_zone_toolkit.core.results import AnalysisResult, Emprise

# Le rapport est toujours du HTML ; le gabarit est nommé `.j2` (que
# select_autoescape() n'activerait pas) → échappement inconditionnel pour
# neutraliser toute injection via le contenu variable (nom de couche, etc.).
# La carte reste intacte : `{{ carte }}` est un data-URI base64 (alphabet
# A-Za-z0-9+/=, aucun caractère HTML-spécial).
_env = Environment(
    loader=PackageLoader("crs_zone_toolkit", "templates"),
    autoescape=True,
)


def _carte_base64(
    layer: gpd.GeoDataFrame, grid: gpd.GeoDataFrame, *, profile: RegionProfile
) -> str:
    """Carte auto-portée : empreinte réelle de la couche sur la grille des fuseaux.

    Couche et grille reprojetées vers le CRS d'affichage du profil
    (`multi_zones["csrs"]`, Québec Lambert) pour des formes non déformées — le
    code EPSG vient du profil (TP-40). API objet matplotlib (headless/CI-safe).
    """
    display_crs = profile.multi_zones["csrs"]
    grille = grid.to_crs(display_crs)
    couche = layer.to_crs(display_crs)

    fig = Figure(figsize=(8, 4.2), dpi=110)
    FigureCanvasAgg(fig)  # rattache le canvas Agg (headless/CI-safe) à la figure
    ax = fig.add_subplot(111)
    # Palette neutre au thème : lisible sur une plaque claire ET sombre (un seul
    # PNG, fond transparent → le rapport commutable montre l'un ou l'autre). Le
    # gris moyen et le bleu saturé conservent leur contraste des deux côtés ;
    # la bande de fuseau reste une teinte translucide bleu-gris à peine posée.
    grille.boundary.plot(ax=ax, color="#9a9a93", linewidth=0.8)
    grille.plot(ax=ax, color="#7f92ad", alpha=0.16, edgecolor="none")
    couche.plot(ax=ax, color="#2f7fdd", linewidth=1.6, markersize=8)
    for _, cell in grille.iterrows():
        c = cell.geometry.centroid
        ax.annotate(
            f"F{int(cell.zone)}",
            (c.x, c.y),
            ha="center",
            va="center",
            fontsize=8,
            color="#8b8b83",
        )
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.tight_layout(pad=0.4)

    tampon = io.BytesIO()
    # transparent=True : le fond de figure et d'axes reste vide (alpha 0) pour
    # que la plaque du thème transparaisse (SPEC §7, rapport commutable).
    fig.savefig(tampon, format="png", transparent=True)
    encode = base64.b64encode(tampon.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encode}"


def _fr(x: float, dec: int = 1) -> str:
    """Nombre en français — délègue au point de vérité unique (DT-05)."""
    return msg.fr_nombre(x, dec)


def _ppm_signe(v: float, dec: int = 0) -> str:
    """ppm signé : `+` ASCII pour les valeurs positives/nulles, `−` Unicode (U+2212,
    conforme au gabarit visuel interne) pour les négatives — le tiret
    ASCII de `f"{v:+.0f}"` n'est pas un signe moins typographique."""
    s = f"{v:+.{dec}f}"
    return s.replace("-", "−", 1)


def _echelle_ppm(
    paires: list[tuple[float, float]], *, seuil: float
) -> tuple[list[dict[str, Any]], float]:
    """Géométrie de l'échelle de distorsion divergente, partagée par les candidats.

    `paires` : `[(min_ppm, max_ppm), …]`. Domaine symétrique commun `[-dom, +dom]`
    (dom = millier supérieur du pire |écart|) pour que les candidats soient
    comparables sur une même règle. Positions en pourcentage de largeur (0 à
    gauche, `dom` à droite ; le 0 ppm tombe donc au centre). Un candidat qui
    franchit ±`seuil` reçoit un `facteur` ≈ pire écart / seuil (sinon `None`).
    """
    valeurs = [v for paire in paires for v in paire]
    maxabs = max((abs(v) for v in valeurs), default=float(seuil))
    dom = math.ceil(maxabs / 1000) * 1000 or 1000

    def pos(v: float) -> float:
        return (v + dom) / (2 * dom) * 100.0

    geoms: list[dict[str, Any]] = []
    for mn, mx in paires:
        pire = max(abs(mn), abs(mx))
        # `seuil > 0` garde `hors_seuil` et `facteur` cohérents : sans tolérance
        # définie (seuil = 0), aucun candidat n'est signalé (badge ≡ texte).
        hors = seuil > 0 and pire > seuil
        geoms.append(
            {
                "zero": pos(0),
                "tol_left": pos(-seuil),
                "tol_width": pos(seuil) - pos(-seuil),
                "seg_left": pos(mn),
                "seg_width": max(pos(mx) - pos(mn), 0.6),
                "min_pos": pos(mn),
                "max_pos": pos(mx),
                "hors_seuil": hors,
                "facteur": round(pire / seuil) if hors else None,
            }
        )
    return geoms, dom


def _alternative_vm(alt: dict[str, Any]) -> dict[str, Markup]:
    """View-model d'une alternative (clés réelles du moteur : {'action', 'zones'}).

    Les libellés viennent de messages.py (copie maîtrisée par le développeur) :
    marqués `Markup` pour rendre les apostrophes littérales sous autoescape, sans
    rouvrir de faille (aucune donnée utilisateur n'y transite).
    """
    action = alt.get("action")
    if action == "split":
        return {
            "titre": Markup(msg.ALT_SPLIT_TITRE),
            "description": Markup(msg.alt_split_desc(alt.get("zones", []))),
        }
    # `core/analysis._decide` ne construit jamais d'alternative "zone"/"lambert" :
    # seule l'action top-level peut valoir ça, les alternatives sont toujours "split".
    return {"titre": Markup.escape(str(action)), "description": Markup("")}


def _note_datum(famille: str) -> Markup:
    return Markup(msg.NOTE_DATUM.get(famille, msg.NOTE_DATUM_DEFAUT))


def _emprise_texte(e: Emprise) -> str:
    def lon(v: float) -> str:
        return f"{abs(v):.2f}°{'O' if v < 0 else 'E'}"

    def lat(v: float) -> str:
        return f"{abs(v):.2f}°{'N' if v >= 0 else 'S'}"

    return f"{lon(e.lon_min)} → {lon(e.lon_max)} · {lat(e.lat_min)} → {lat(e.lat_max)}"


def _crs_declare(crs_entree: dict[str, Any]) -> str:
    """Libellé du CRS déclaré à partir de `crs_entree` (pas de clé `libelle` en sortie moteur)."""
    epsg = crs_entree.get("epsg")
    etiquette = crs_entree.get("etiquette", "")
    if epsg is not None:
        return f"EPSG:{epsg} ({etiquette})"
    return str(etiquette)


def _version() -> str:
    import crs_zone_toolkit

    return crs_zone_toolkit.__version__


def _contexte(
    analysis: AnalysisResult,
    layer: gpd.GeoDataFrame,
    carte: str,
    generated_at: datetime,
    *,
    profile: RegionProfile,
) -> dict[str, Any]:
    seuil = float(analysis.parametres.get("distorsion_max_ppm", 0))
    geoms, _ = _echelle_ppm([(x.min_ppm, x.max_ppm) for x in analysis.distorsions], seuil=seuil)
    # Copie maîtrisée par messages.py → Markup (apostrophes littérales sous
    # autoescape). Le contenu variable d'origine utilisateur (couche, crs_declare)
    # n'est PAS marqué : il reste échappé par l'autoescape (défense en profondeur).
    famille_libelle = Markup(msg.FAMILLE_LIBELLE.get(analysis.famille, msg.FAMILLE_LIBELLE_DEFAUT))
    return {
        "couche": analysis.couche,
        "region": analysis.parametres.get("region", ""),
        "profil_nom": profile.nom,
        "genere_le": generated_at.strftime("%Y-%m-%d %H:%M"),
        "version": _version(),
        "n_entites": _fr(len(layer), 0),
        "type_geometrie": analysis.type_geometrie,
        "crs_declare": _crs_declare(analysis.crs_entree),
        "famille_libelle": famille_libelle,
        "emprise_texte": _emprise_texte(analysis.emprise),
        # Chaînes brutes (PAS de Markup) : l'autoescape les échappe. Épingle
        # l'invariant qu'un futur avertissement reprenant une entrée utilisateur
        # ne pourra jamais injecter de HTML (test dédié). Les apostrophes rendues
        # `&#39;` s'affichent identiquement.
        "avertissements": list(analysis.avertissements),
        "carte": carte,
        "fuseaux": [
            {
                "zone": z.zone,
                "epsg": z.epsg,
                "pct": round(z.part * 100, 1),
                "pct_txt": _fr(z.part * 100) + " %",
            }
            for z in analysis.zones_traversees
        ],
        "distorsions": [
            {
                "libelle": x.libelle,
                "epsg": x.epsg,
                "min": _ppm_signe(x.min_ppm),
                "moy": _ppm_signe(x.moy_ppm),
                "max": _ppm_signe(x.max_ppm),
                "hors_seuil": g["hors_seuil"],
                "facteur": g["facteur"],
                "scale": g,
            }
            for x, g in zip(analysis.distorsions, geoms, strict=True)
        ],
        "seuil_ppm": f"{seuil:.0f}",
        "action": analysis.recommandation.action,
        "reco_titre": Markup(analysis.recommandation.cible_libelle),
        "cible_epsg": analysis.recommandation.cible_epsg,
        "cible_libelle": Markup(analysis.recommandation.cible_libelle),
        "motif": Markup(analysis.recommandation.motif),
        "alternatives": [_alternative_vm(a) for a in analysis.recommandation.alternatives],
        "note_datum": _note_datum(analysis.famille),
        "p": analysis.parametres,
    }


def render_html(
    analysis: AnalysisResult,
    layer: gpd.GeoDataFrame,
    *,
    profile: RegionProfile,
    grid: gpd.GeoDataFrame,
    generated_at: datetime,
) -> str:
    """Rend le rapport HTML complet auto-porté (SPEC §7)."""
    carte = _carte_base64(layer, grid, profile=profile)
    contexte = _contexte(analysis, layer, carte, generated_at, profile=profile)
    return _env.get_template("rapport.html.j2").render(**contexte)


def _ecrire(
    html: str, source: Path, *, out_dir: Path | None, overwrite: bool, generated_at: datetime
) -> Path:
    """Écrit `<nom>_analyse_crs_<horodatage>.html` à côté de la source (ou dans out_dir).

    L'horodatage (`AAAAMMJJ-HHMMSS`, celui du rapport) rend chaque nom unique :
    deux analyses successives ne s'écrasent plus, l'historique est conservé.
    """
    dossier = out_dir if out_dir is not None else source.parent
    horodatage = generated_at.strftime("%Y%m%d-%H%M%S")
    chemin = dossier / f"{source.stem}_analyse_crs_{horodatage}.html"
    if chemin.exists() and not overwrite:
        raise OutputExistsError(msg.fichier_existant(str(chemin)))
    dossier.mkdir(parents=True, exist_ok=True)
    chemin.write_text(html, encoding="utf-8")
    return chemin
