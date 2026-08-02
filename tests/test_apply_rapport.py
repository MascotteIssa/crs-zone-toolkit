"""DT-23 — `apply` produit le rapport qu'il promet (observation N14).

Le menu affichait `[0] Annuler (relire le rapport avant de décider)` alors
qu'`apply` n'écrivait **aucun** HTML : `render_html`/`_ecrire` n'existaient que
dans `analyze`. Les trois exécutions du §6 du test manuel ne laissaient que le
`.gpkg` et le journal. C'est le **« pire moment du parcours »** déclaré par
l'exécutant (§11.3).

**Le texte du menu fixe le moment.** « Relire le rapport **avant de décider** »
n'a de sens que si le rapport existe **quand le menu s'affiche** — pas après.
C'est ce que garde `test_dt23_le_rapport_existe_deja_quand_le_menu_s_affiche`,
et c'est la seule assertion qui distingue une promesse tenue d'un fichier écrit
trop tard.

**Périmètre arbitré** (protocole §9, N14) : mode **interactif** et
**`--choice split`** — là où six fichiers sortent d'une seule décision et où le
rapport est décisif. Pas `--auto`, qui ne promet rien et n'ouvre aucun menu.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString
from typer.testing import CliRunner

from crs_zone_toolkit.cli import app

runner = CliRunner()


def _deux_fuseaux(tmp_path: Path) -> Path:
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2, 46.4)]
    lignes += [
        LineString([(-73.5, 46.0), (-72.5, 46.0)]),
        LineString([(-73.4, 46.3), (-72.6, 46.3)]),
    ]
    chemin = tmp_path / "routes.geojson"
    gpd.GeoDataFrame(geometry=lignes, crs=4326).to_file(chemin, driver="GeoJSON")
    return chemin


def _rapports(dossier: Path) -> list[Path]:
    return sorted(dossier.glob("routes_analyse_crs_*.html"))


def _interactif(monkeypatch, reponses: list[str], avant_invite=None) -> None:
    """Simule un terminal ; `avant_invite` est appelé à chaque invite."""
    monkeypatch.setattr("crs_zone_toolkit.cli._est_interactif", lambda: True)
    suite = iter(reponses)

    def _repondre(*_a: object, **kw: object) -> object:
        if avant_invite is not None:
            avant_invite()
        valeur = next(suite)
        convertir = kw.get("type")
        return convertir(valeur) if callable(convertir) else valeur

    monkeypatch.setattr("typer.prompt", _repondre)


def test_dt23_le_rapport_existe_deja_quand_le_menu_s_affiche(tmp_path, monkeypatch) -> None:
    """Le cœur de N14 : « relire le rapport AVANT de décider ».

    Un rapport écrit après la décision satisferait « apply produit un rapport »
    tout en laissant la promesse du menu aussi creuse qu'avant.
    """
    src = _deux_fuseaux(tmp_path)
    sortie = tmp_path / "s"
    vus: list[int] = []
    _interactif(monkeypatch, ["1"], avant_invite=lambda: vus.append(len(_rapports(sortie))))

    res = runner.invoke(app, ["apply", str(src), "--out", str(sortie)])

    assert res.exit_code == 0
    assert vus == [1], "le rapport doit être écrit avant que le menu ne soit présenté"


def test_dt23_choice_split_produit_le_rapport(tmp_path) -> None:
    """Le cas où le rapport est le plus utile : six fichiers d'une seule décision."""
    src = _deux_fuseaux(tmp_path)
    sortie = tmp_path / "s"

    res = runner.invoke(app, ["apply", str(src), "--choice", "split", "--out", str(sortie)])

    assert res.exit_code == 0
    assert len(_rapports(sortie)) == 1
    assert len(list(sortie.glob("routes_zone*.gpkg"))) >= 2


def test_dt23_annuler_laisse_le_rapport_a_relire(tmp_path, monkeypatch) -> None:
    """`[0]` sert précisément à aller le lire : il doit rester."""
    src = _deux_fuseaux(tmp_path)
    sortie = tmp_path / "s"
    _interactif(monkeypatch, ["0"])

    res = runner.invoke(app, ["apply", str(src), "--out", str(sortie)])

    assert res.exit_code == 0
    assert len(_rapports(sortie)) == 1
    assert not list(sortie.glob("*.gpkg")), "aucune donnée écrite, c'est la promesse de [0]"


def test_dt23_auto_n_ecrit_aucun_rapport(tmp_path) -> None:
    """Contre-épreuve : `--auto` n'ouvre aucun menu et ne promet rien (périmètre arbitré)."""
    src = _deux_fuseaux(tmp_path)
    sortie = tmp_path / "s"

    res = runner.invoke(app, ["apply", str(src), "--auto", "--out", str(sortie)])

    assert res.exit_code == 0
    assert _rapports(sortie) == []
    assert list(sortie.glob("*.gpkg")), "mais les sorties, elles, sont bien là"


def test_dt23_choice_hors_split_n_ecrit_aucun_rapport(tmp_path) -> None:
    """Contre-épreuve : sans elle, « écrire toujours » passerait les tests ci-dessus."""
    src = _deux_fuseaux(tmp_path)
    sortie = tmp_path / "s"

    res = runner.invoke(app, ["apply", str(src), "--choice", "lambert", "--out", str(sortie)])

    assert res.exit_code == 0
    assert _rapports(sortie) == []


def test_dt23_sans_out_le_rapport_va_a_cote_de_la_couche(tmp_path, monkeypatch) -> None:
    """Même défaut que les sorties d'`apply` : le dossier de la couche."""
    src = _deux_fuseaux(tmp_path)
    _interactif(monkeypatch, ["0"])

    res = runner.invoke(app, ["apply", str(src)])

    assert res.exit_code == 0
    assert len(_rapports(tmp_path)) == 1


def test_dt23_session_non_interactive_n_ecrit_rien(tmp_path) -> None:
    """Garde : le refus « session non interactive » ne doit laisser aucun fichier derrière lui."""
    src = _deux_fuseaux(tmp_path)
    sortie = tmp_path / "s"

    res = runner.invoke(app, ["apply", str(src), "--out", str(sortie)])

    assert res.exit_code == 2
    assert not sortie.exists() or list(sortie.iterdir()) == []
