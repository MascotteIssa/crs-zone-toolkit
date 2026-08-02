"""_ecrire : nommage <nom>_analyse_crs_<horodatage>.html + garde anti-écrasement."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from crs_zone_toolkit.core.errors import OutputExistsError
from crs_zone_toolkit.core.report import _ecrire

_QUAND = datetime(2026, 7, 17, 23, 39, 5, tzinfo=UTC)


def test_nommage_horodate_et_contenu(tmp_path: Path) -> None:
    """Le nom porte l'horodatage → deux analyses ne s'écrasent plus (historique gardé)."""
    src = tmp_path / "routes.gpkg"
    chemin = _ecrire("<html>ok</html>", src, out_dir=None, overwrite=False, generated_at=_QUAND)
    assert chemin.name == "routes_analyse_crs_20260717-233905.html"
    assert chemin.read_text(encoding="utf-8") == "<html>ok</html>"


def test_refuse_ecraser_sans_overwrite(tmp_path: Path) -> None:
    """Même horodatage → même nom → la garde anti-écrasement joue toujours."""
    src = tmp_path / "routes.gpkg"
    _ecrire("<html>1</html>", src, out_dir=None, overwrite=False, generated_at=_QUAND)
    with pytest.raises(OutputExistsError):
        _ecrire("<html>2</html>", src, out_dir=None, overwrite=False, generated_at=_QUAND)


def test_overwrite_remplace(tmp_path: Path) -> None:
    src = tmp_path / "routes.gpkg"
    _ecrire("<html>1</html>", src, out_dir=None, overwrite=False, generated_at=_QUAND)
    chemin = _ecrire("<html>2</html>", src, out_dir=None, overwrite=True, generated_at=_QUAND)
    assert chemin.read_text(encoding="utf-8") == "<html>2</html>"


def test_out_dir_dedie(tmp_path: Path) -> None:
    src = tmp_path / "data" / "routes.gpkg"
    src.parent.mkdir()
    sortie = tmp_path / "rapports"
    chemin = _ecrire("<html>ok</html>", src, out_dir=sortie, overwrite=False, generated_at=_QUAND)
    assert chemin == sortie / "routes_analyse_crs_20260717-233905.html"


def test_horodatage_distinct_ne_s_ecrase_pas(tmp_path: Path) -> None:
    """Deux horodatages différents → deux fichiers distincts, aucun écrasement."""
    src = tmp_path / "routes.gpkg"
    t1 = datetime(2026, 7, 17, 23, 39, 5, tzinfo=UTC)
    t2 = datetime(2026, 7, 17, 23, 40, 12, tzinfo=UTC)
    c1 = _ecrire("<html>1</html>", src, out_dir=None, overwrite=False, generated_at=t1)
    c2 = _ecrire("<html>2</html>", src, out_dir=None, overwrite=False, generated_at=t2)
    assert c1 != c2
    assert c1.exists() and c2.exists()
