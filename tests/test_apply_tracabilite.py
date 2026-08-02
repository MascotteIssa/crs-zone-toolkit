"""DT-27 — ce qu'`apply` dit et consigne de sa propre décision (observations N4, N5).

Deux demandes de `CLI_UX` §4/§5, séparables mais de même objet — la décision
doit être **lisible après coup**, à l'écran comme au journal :

- **N4** : `--auto` n'affichait **aucune** ligne annonçant le mode automatique.
  Une sortie `--auto` ne se distinguait d'un choix humain qu'en relisant
  `decision.origine` dans le journal.
- **N5** : `decision.note` restait `null` alors que `CLI_UX` §4 promet un choix
  hors recommandation « journalisé ». **Cause trouvée** : la note existait déjà,
  mais gardée par `decision.origine == "choice"` — ce qui exclut le chemin
  **interactif**, précisément celui où un humain choisit délibérément contre la
  recommandation. Le test manuel §6.8 est passé par le menu : d'où le `null`.

*La confirmation supplémentaire réclamée par `CLI_UX` §4 est **écartée**
(maquette amendée) : choisir `[2]` puis saisir un numéro de fuseau est déjà
l'acte conscient — une invite de plus ajouterait de la friction sans
information.*
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString
from typer.testing import CliRunner

from crs_zone_toolkit.cli import app
from crs_zone_toolkit.core import messages as msg

runner = CliRunner()


def _deux_fuseaux(tmp_path: Path) -> Path:
    """Lignes à cheval sur 75°O + deux lignes propres au fuseau 8 (recommandation = fuseau 8)."""
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    lignes += [
        LineString([(-73.5, 46.0), (-72.5, 46.0)]),
        LineString([(-73.4, 46.3), (-72.6, 46.3)]),
    ]
    chemin = tmp_path / "routes.geojson"
    gpd.GeoDataFrame(geometry=lignes, crs=4326).to_file(chemin, driver="GeoJSON")
    return chemin


def _journal(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "routes_journal.json").read_text(encoding="utf-8"))


# ── N5 — la note du journal ────────────────────────────────────────────────


def test_dt27_choix_interactif_contre_la_reco_est_journalise(tmp_path, monkeypatch) -> None:
    """Le trou de N5 : `origine == "interactive"` ne produisait aucune note.

    C'est pourtant le chemin où l'humain choisit **délibérément** contre la
    recommandation, donc celui où la trace importe le plus.
    """
    src = _deux_fuseaux(tmp_path)
    monkeypatch.setattr("crs_zone_toolkit.cli._est_interactif", lambda: True)
    reponses = iter(["2", "9"])  # [2] autre fuseau, puis le 9 (≠ recommandation)

    def _repondre(*_a: object, **kw: object) -> object:
        # `typer.prompt(..., type=int)` convertit ; le stub doit en faire autant,
        # sinon la zone reste une chaîne et `fuseau_par_zone` lève un KeyError.
        valeur = next(reponses)
        convertir = kw.get("type")
        return convertir(valeur) if callable(convertir) else valeur

    monkeypatch.setattr("typer.prompt", _repondre)

    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)])

    assert res.exit_code == 0
    decision = _journal(tmp_path)["decision"]
    assert decision["origine"] == "interactive"
    assert decision["note"] == msg.NOTE_CHOIX_HORS_RECO


def test_dt27_choix_interactif_conforme_a_la_reco_ne_note_rien(tmp_path, monkeypatch) -> None:
    """Contre-épreuve : sans elle, noter *toujours* passerait le test ci-dessus."""
    src = _deux_fuseaux(tmp_path)
    monkeypatch.setattr("crs_zone_toolkit.cli._est_interactif", lambda: True)
    monkeypatch.setattr("typer.prompt", lambda *a, **k: "1")  # [1] suivre la recommandation

    res = runner.invoke(app, ["apply", str(src), "--out", str(tmp_path)])

    assert res.exit_code == 0
    decision = _journal(tmp_path)["decision"]
    assert decision["origine"] == "interactive"
    assert decision["note"] is None


def test_dt27_le_mode_auto_ne_note_rien(tmp_path) -> None:
    """Contre-épreuve : `--auto` applique la recommandation, il n'y a rien à signaler."""
    src = _deux_fuseaux(tmp_path)

    res = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)])

    assert res.exit_code == 0
    assert _journal(tmp_path)["decision"]["note"] is None


def test_dt27_le_contrat_json_du_journal_est_inchange(tmp_path) -> None:
    """Garde : DT-27 change une **valeur**, jamais la forme du journal (SPEC §9)."""
    src = _deux_fuseaux(tmp_path)
    runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)])

    journal = _journal(tmp_path)
    assert journal["schema_version"] == 1
    assert set(journal["decision"]) == {"choix", "origine", "zone", "cible_epsg", "note"}


# ── N4 — l'annonce du mode automatique ─────────────────────────────────────


def test_dt27_auto_annonce_le_mode_et_la_cible(tmp_path) -> None:
    """`CLI_UX` §5 : « Mode --auto : application de la recommandation (…, EPSG:…) ».

    Vérifié par le **constructeur de message** — la présence à l'écran relève du
    test doré de l'écran §5 (TEST_PLAN §7).
    """
    ligne = msg.apply_mode_auto("MTM fuseau 8", 2950, action="zone")
    assert "--auto" in ligne
    assert "EPSG:2950" in ligne
    assert "MTM fuseau 8" in ligne


def test_dt27_auto_sans_recommandation_ne_nomme_aucun_epsg(tmp_path) -> None:
    """Leçon de DT-22 : la sentinelle `cible_epsg = 0` ne doit fuir dans aucune ligne neuve.

    Une couche 100 % hors profil sous `--auto` n'a pas de cible ; annoncer
    « application de la recommandation (EPSG:0) » rejouerait le bug qu'on vient
    de corriger.
    """
    ligne = msg.apply_mode_auto("", 0, action="aucune")
    assert "EPSG" not in ligne
    assert "aucune" in ligne.lower()


def test_dt27_la_ligne_auto_est_bien_emise_par_la_commande(tmp_path, monkeypatch) -> None:
    """Le câblage, pas seulement la chaîne — par espion, sans assertion de texte.

    Sans cette garde, `apply_mode_auto` pouvait exister, être testée, et
    n'être appelée par personne : la suite passait verte avant comme après
    (le piège relevé à DT-22).
    """
    appels: list[str] = []
    vrai = msg.apply_mode_auto

    def espion(libelle: str, epsg: int, *, action: str) -> str:
        appels.append(action)
        return vrai(libelle, epsg, action=action)

    monkeypatch.setattr(msg, "apply_mode_auto", espion)
    src = _deux_fuseaux(tmp_path)

    res = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(tmp_path)])

    assert res.exit_code == 0
    assert appels == ["zone"], "la ligne doit être émise une fois, avec l'action réelle"


def test_dt27_la_ligne_auto_ne_parait_pas_sans_auto(tmp_path, monkeypatch) -> None:
    """Contre-épreuve : `--choice` n'est pas le mode automatique (CLI_UX §5)."""
    appels: list[str] = []
    monkeypatch.setattr(msg, "apply_mode_auto", lambda *a, **k: appels.append("x") or "…")
    src = _deux_fuseaux(tmp_path)

    res = runner.invoke(app, ["apply", str(src), "--choice", "lambert", "--out", str(tmp_path)])

    assert res.exit_code == 0
    assert appels == []
