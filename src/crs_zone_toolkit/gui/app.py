"""Coquille pywebview : fenêtre native chargeant gui/web/index.html, sans navigateur visible.

Vérifié (pywebview 6.2.1, uv add pywebview) : les appels JS -> `js_api`
transitent par un serveur HTTP local (`webview/http.py`, `ThreadedAdapter` /
`ThreadingMixIn`), chaque appel s'exécutant sur son propre thread de serveur,
distinct du thread d'interface principal. `Api.analyze`/`Api.apply` peuvent
donc appeler `service.run_analyze`/`run_apply` de façon synchrone : la
fenêtre reste réactive sans threading manuel côté application.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path
from typing import Any

import webview

from crs_zone_toolkit.core.results import Decision
from crs_zone_toolkit.gui import service

_WEB_DIR = Path(__file__).parent / "web"
_INDEX_HTML = _WEB_DIR / "index.html"


class Api:
    """Méthodes exposées au JS de gui/web/index.html via `pywebview.api`."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None

    def set_window(self, window: webview.Window) -> None:
        self._window = window

    def pick_file(self) -> str | None:
        if self._window is None:
            return None
        selection = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            file_types=("Couches géospatiales (*.gpkg;*.shp;*.geojson)", "Tous les fichiers (*.*)"),
        )
        return selection[0] if selection else None

    def pick_folder(self) -> str | None:
        if self._window is None:
            return None
        selection = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return selection[0] if selection else None

    def analyze(
        self, path: str, out_dir: str | None = None, assume_crs: str | None = None
    ) -> dict[str, Any]:
        source = Path(path)
        cible = Path(out_dir) if out_dir else None
        result = service.run_analyze(source, assume_crs=assume_crs)
        report_path = service.run_report(source, out_dir=cible, assume_crs=assume_crs)
        return {"analysis": result.to_dict(), "report_path": str(report_path)}

    def apply(self, path: str, choice: str, out_dir: str | None = None) -> dict[str, Any]:
        decision: Decision = service.decision_from_choice(choice)
        cible = Path(out_dir) if out_dir else None
        result = service.run_apply(Path(path), decision, out_dir=cible)
        return result.to_dict()

    def generate_grid(self, out_path: str, out_format: str, clip: bool) -> dict[str, Any]:
        chemin, n, _ = service.run_generate_grid(
            out=Path(out_path), out_format=out_format, clip=clip
        )
        return {"path": str(chemin), "n": n}

    def open_path(self, path: str) -> None:
        """Ouvre un fichier ou un dossier avec l'application par défaut du système.

        La garde `sys.platform` n'est pas décorative : `os.startfile` n'existe
        que sous Windows, et sans elle mypy échoue sur toute autre plateforme —
        c'est ce qui a mis la CI Ubuntu au rouge du 24 au 25 août 2026, mypy
        s'exécutant avant pytest (donc la suite ne tournait plus sous Linux).
        Le repli `webbrowser` couvre les autres systèmes sans dépendance neuve.
        """
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 — chemin produit par le moteur, pas une entrée externe
        else:
            webbrowser.open(Path(path).resolve().as_uri())


def main() -> None:
    api = Api()
    # Taille fixe (non redimensionnable) : la maquette (docs/maquettes/Web habillé/
    # crszone-bureau-maquette.html) est calibrée pour une largeur de contenu de
    # 900px ; un redimensionnement/maximisation libre laisserait un vide autour
    # d'elle (le contenu ne remplit pas la fenêtre). Retenu plutôt qu'un
    # redesign responsive, qui toucherait la maquette déjà validée.
    window = webview.create_window(
        "crszone", str(_INDEX_HTML), js_api=api, width=960, height=720, resizable=False
    )
    if window is None:
        raise RuntimeError("Échec de création de la fenêtre pywebview.")
    api.set_window(window)
    webview.start()
