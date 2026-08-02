"""Carte du rapport : PNG matplotlib embarqué en data-URI base64 (auto-portage)."""

import base64
import io

import geopandas as gpd
from PIL import Image
from shapely.geometry import LineString

from crs_zone_toolkit.core.report import _carte_base64


def _png(qc_profile, qc_grid) -> bytes:
    lignes = [LineString([(-76.16, lat), (-74.16, lat)]) for lat in (46.0, 46.2)]
    layer = gpd.GeoDataFrame(geometry=lignes, crs=4326)
    uri = _carte_base64(layer, qc_grid, profile=qc_profile)
    assert uri.startswith("data:image/png;base64,")
    return base64.b64decode(uri.split(",", 1)[1])


def test_carte_est_un_data_uri_png_valide(qc_profile, qc_grid) -> None:
    brut = _png(qc_profile, qc_grid)
    assert brut[:8] == b"\x89PNG\r\n\x1a\n"  # signature PNG
    assert len(brut) > 1000  # image non vide


def test_carte_a_un_fond_transparent(qc_profile, qc_grid) -> None:
    """Fond transparent : la carte épouse le thème (clair ou sombre) au lieu
    d'imposer un rectangle blanc opaque — le rapport est commutable."""
    img = Image.open(io.BytesIO(_png(qc_profile, qc_grid)))
    assert img.mode == "RGBA"  # canal alpha présent
    assert img.getpixel((0, 0))[3] == 0  # coin haut-gauche = totalement transparent
