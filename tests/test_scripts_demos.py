"""DT-21 — couverture de `scripts/regenerer_demos.py`.

`scripts/` vivait hors du périmètre de la suite. La Phase C l'a payé : la
Task 3 a rendu obligatoire le paramètre `famille_cible` de
`affichage.resume_analyse`, `regenerer_gif` l'appelait sans lui, et **ni
l'implémenteur ni le relecteur ne l'ont vu** — la casse n'est apparue qu'en
*exécutant* le script à la Task 4.

Deux niveaux, parce qu'aucun seul ne suffit :

1. **Liaison des appels** (`test_les_appels_au_paquet_lient`) — vérifie par AST
   que chaque appel du script à une fonction du paquet **satisfait la signature
   réelle**. C'est le test qui aurait attrapé la Phase C, et il couvre
   `regenerer_gif`/`regenerer_captures`, **inexécutables ici** (playwright +
   Pillow, hors dépendances de test).
2. **Exécution réelle** — les deux fonctions qui n'exigent qu'un moteur et une
   console sont invoquées de bout en bout sur une couche fabriquée.

La couche de démonstration par défaut (`tests/user_test/data/`) est **gitignorée**
et en lecture seule : chaque test fabrique la sienne dans `tmp_path`.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import io
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import geopandas as gpd
import pytest
from shapely.geometry import box

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "scripts" / "regenerer_demos.py"


def _charger_script() -> ModuleType:
    """Importe le script par chemin — `scripts/` n'est pas un paquet."""
    spec = importlib.util.spec_from_file_location("regenerer_demos", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return _charger_script()


@pytest.fixture
def couche(tmp_path: Path) -> Path:
    """Polygone du fuseau 8 (autour du MC -73,5), écrit en GeoJSON dans tmp_path."""
    gdf = gpd.GeoDataFrame(geometry=[box(-74.0, 45.8, -73.0, 46.4)], crs=4326)
    chemin = tmp_path / "demo_fuseau8.geojson"
    gdf.to_file(chemin, driver="GeoJSON")
    return chemin


# ── 1. Liaison des appels — le test qui aurait attrapé la Phase C ───────────


def test_les_appels_au_paquet_lient() -> None:
    """Chaque appel du script à une fonction du paquet satisfait sa signature.

    Attrape la classe de défaut de DT-21 : un paramètre rendu obligatoire dans
    le paquet, non répercuté au site d'appel du script. Couvre les fonctions
    que la suite ne peut pas exécuter (`regenerer_gif`, `regenerer_captures`).
    """
    from crs_zone_toolkit import _charger_et_analyser, affichage
    from crs_zone_toolkit.core import report as _report
    from crs_zone_toolkit.core.targets import target_family

    # Attribut appelé -> objet réel. Le script appelle ces fonctions par
    # attribut (`affichage.resume_analyse`) ou par nom nu (`target_family`).
    cibles: dict[str, Any] = {
        "resume_analyse": affichage.resume_analyse,
        "render_html": _report.render_html,
        "_ecrire": _report._ecrire,
        "_charger_et_analyser": _charger_et_analyser,
        "target_family": target_family,
    }

    arbre = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    sentinelle = object()
    vus: set[str] = set()

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        f = noeud.func
        nom = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
        if nom not in cibles:
            continue
        # Un dépliage `*args`/`**kwargs` rend la liaison indécidable : on passe.
        if any(isinstance(a, ast.Starred) for a in noeud.args) or any(
            k.arg is None for k in noeud.keywords
        ):
            continue

        vus.add(nom)
        signature = inspect.signature(cibles[nom])
        try:
            signature.bind(
                *[sentinelle] * len(noeud.args),
                **{k.arg: sentinelle for k in noeud.keywords if k.arg is not None},
            )
        except TypeError as exc:  # pragma: no cover - le message porte le diagnostic
            pytest.fail(
                f"{SCRIPT.name}:{noeud.lineno} — l'appel à `{nom}` ne satisfait plus "
                f"la signature du paquet `{nom}{signature}` : {exc}"
            )

    # Garde-fou : si le script est réécrit et n'appelle plus rien du paquet, le
    # test passerait à vide et ne protégerait plus rien.
    assert "resume_analyse" in vus, (
        "aucun appel à `resume_analyse` trouvé dans le script — c'est l'appel "
        "même qui a cassé en Phase C ; ce test ne protège plus rien."
    )


# ── 2. Exécution réelle des fonctions sans dépendance de rendu ─────────────


def test_regenerer_extrait_remplace_le_bloc(
    script: ModuleType, couche: Path, tmp_path: Path
) -> None:
    """`regenerer_extrait` produit le bloc depuis le VRAI code d'affichage."""
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Titre\n\nAvant.\n\n{script.MARQUEUR_EXTRAIT_DEBUT}\n"
        f"```console\nPÉRIMÉ\n```\n{script.MARQUEUR_EXTRAIT_FIN}\n\nAprès.\n",
        encoding="utf-8",
    )

    rendu = script.regenerer_extrait(couche, readme=readme)

    assert rendu == readme
    texte = readme.read_text(encoding="utf-8")
    assert "PÉRIMÉ" not in texte
    assert texte.startswith("# Titre")  # le hors-marqueurs est préservé
    assert texte.endswith("Après.\n")
    assert f"$ crszone analyze {couche.name}" in texte
    # Aucune espace de fin : le hook pre-commit `trailing-whitespace` couvre README.md.
    bloc = texte.split(script.MARQUEUR_EXTRAIT_DEBUT, 1)[1].split(script.MARQUEUR_EXTRAIT_FIN, 1)[0]
    assert not [ligne for ligne in bloc.splitlines() if ligne != ligne.rstrip()]


def test_regenerer_bloc_apply_remplace_le_bloc(
    script: ModuleType, couche: Path, tmp_path: Path
) -> None:
    """DT-17 : le bloc `apply --auto` du README est entré au périmètre du script.

    C'est celui qui est parti périmé **deux fois** — clôture de la Phase C, puis
    passe corrective — parce qu'un bloc périmé PAR SOUSTRACTION ne contient pas
    les marqueurs de ce qui lui manque : aucune recherche textuelle ne pouvait
    le rattraper.
    """
    readme = tmp_path / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# T",
                "",
                script.MARQUEUR_APPLY_DEBUT,
                "```console",
                "PÉRIMÉ",
                "```",
                script.MARQUEUR_APPLY_FIN,
                "",
                "fin.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    script.regenerer_bloc_apply(couche, readme=readme)

    texte = readme.read_text(encoding="utf-8")
    assert "PÉRIMÉ" not in texte
    assert texte.startswith("# T")  # le hors-marqueurs est préservé
    assert texte.endswith("fin.\n")
    assert f"$ crszone apply {couche.name}" in texte
    assert "Mode --auto" in texte, "la ligne de DT-27 doit figurer au bloc"
    assert "Pour appliquer" not in texte, "N2 : apply ne propose plus la commande en cours"


def test_regenerer_bloc_apply_n_ecrit_pas_hors_du_temporaire(
    script: ModuleType, couche: Path, tmp_path: Path
) -> None:
    """Garde : la démonstration ne doit laisser aucun .gpkg derrière elle.

    `regenerer_bloc_apply` se place dans un dossier temporaire pour que les
    chemins affichés restent relatifs — il doit en ressortir, et ne rien semer.
    """
    depart = Path.cwd()
    readme = tmp_path / "README.md"
    readme.write_text(
        f"{script.MARQUEUR_APPLY_DEBUT}\nx\n{script.MARQUEUR_APPLY_FIN}\n", encoding="utf-8"
    )

    script.regenerer_bloc_apply(couche, readme=readme)

    assert Path.cwd() == depart, "le dossier courant doit être rendu"
    assert list(tmp_path.glob("**/*.gpkg")) == []
    assert not (depart / "sorties").exists()


def test_regenerer_extrait_refuse_un_readme_sans_marqueurs(
    script: ModuleType, couche: Path, tmp_path: Path
) -> None:
    """Échec bruyant, et le fichier reste intact."""
    readme = tmp_path / "README.md"
    readme.write_text("# Sans marqueurs\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="Marqueurs"):
        script.regenerer_extrait(couche, readme=readme)

    assert readme.read_text(encoding="utf-8") == "# Sans marqueurs\n"


def test_regenerer_exemple_rapport_ecrit_un_html(
    script: ModuleType, couche: Path, tmp_path: Path
) -> None:
    """`regenerer_exemple_rapport` passe par `render_html` et écrit la sortie."""
    sortie = tmp_path / "exemple.html"

    rendu = script.regenerer_exemple_rapport(couche, sortie=sortie)

    assert rendu == sortie
    assert sortie.is_file()
    html = sortie.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert html.rstrip().endswith("</html>")
    # Auto-portage (SPEC §7) : aucune ressource externe, pas même via le script.
    assert "http://" not in html and "https://" not in html


def test_couche_absente_echoue_sans_rien_ecrire(script: ModuleType, tmp_path: Path) -> None:
    """`_analyser` refuse une couche introuvable avant tout effet de bord."""
    sortie = tmp_path / "jamais_ecrit.html"

    with pytest.raises(SystemExit, match="introuvable"):
        script.regenerer_exemple_rapport(tmp_path / "absente.gpkg", sortie=sortie)

    assert not sortie.exists()


# ── 3. DT-15 (fermeture préventive, décision du 2026-08-02) ────────────────
#
# Ce script n'imprime aujourd'hui aucun caractère hors cp1252 : pas de défaut
# observable à corriger, mais la même classe de défaut a déjà mordu deux fois
# ailleurs (`cli.py`, `publier_release.py`) — un futur « ✓ »/« →» planterait en
# silence sous une console Windows non redirigée en UTF-8. On ferme la famille
# par prévention, avec la même protection, au même endroit dans le flux
# d'exécution (premier geste de `main()`, avant tout le reste).


def test_dt15_forcer_utf8_reconfigure_les_flux(script: ModuleType, monkeypatch) -> None:
    """Même contrat que `cli._forcer_utf8` / `publier_release._forcer_utf8`
    (DT-15) : un flux cp1252 reconfigurable ressort en UTF-8, prêt à écrire
    « ✓ » sans planter."""
    brut_out = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(brut_out, encoding="cp1252"))

    script._forcer_utf8()

    assert sys.stdout.encoding.lower() == "utf-8"
    sys.stdout.write("✓ écrit")
    sys.stdout.flush()
    assert brut_out.getvalue().decode("utf-8") == "✓ écrit"


def test_dt15_main_force_utf8_avant_tout(script: ModuleType, monkeypatch) -> None:
    """`main()` force l'UTF-8 en tout premier, avant même `argparse` — même
    garantie que `cli.py`/`publier_release.py` : la protection ne doit dépendre
    d'aucune étape antérieure (analyse des arguments, régénération) qui
    pourrait elle-même échouer avant d'y arriver."""
    appele: list[bool] = []
    monkeypatch.setattr(script, "_forcer_utf8", lambda: appele.append(True))
    # Court-circuite l'exécution réelle : seul l'ordre d'appel nous intéresse.
    monkeypatch.setattr(script, "regenerer_extrait", lambda *a, **k: Path("x"))

    script.main(["--quoi", "extrait"])

    assert appele == [True]
