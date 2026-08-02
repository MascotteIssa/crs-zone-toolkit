"""Géométrie de l'échelle de distorsion divergente (report._echelle_ppm).

L'échelle remplace la table min/moy/max plate : elle est centrée sur 0 ppm,
partagée entre candidats (même domaine → comparables), et signale de combien
un candidat franchit la tolérance (facteur ×N). Fonction pure, testable seule.
"""

from crs_zone_toolkit.core.report import _echelle_ppm


def test_zero_toujours_au_centre() -> None:
    """Domaine symétrique [-dom, +dom] → le 0 ppm tombe à 50 % de la largeur."""
    geoms, _ = _echelle_ppm([(-100.0, 14784.0)], seuil=200.0)
    assert geoms[0]["zero"] == 50.0


def test_facteur_hors_tolerance() -> None:
    """Un candidat qui franchit ±seuil annonce ≈ ×N (pire écart / seuil, arrondi)."""
    geoms, _ = _echelle_ppm([(-100.0, 14784.0)], seuil=200.0)
    assert geoms[0]["hors_seuil"] is True
    assert geoms[0]["facteur"] == 74  # 14784 / 200 = 73,92 → 74


def test_sous_tolerance_pas_de_facteur() -> None:
    """Un candidat dans la tolérance n'a pas de facteur (rien à signaler)."""
    geoms, _ = _echelle_ppm([(-50.0, 120.0)], seuil=200.0)
    assert geoms[0]["hors_seuil"] is False
    assert geoms[0]["facteur"] is None


def test_segment_reflete_le_signe() -> None:
    """min négatif → le segment démarre à gauche du centre ; max positif → finit à droite."""
    geoms, _ = _echelle_ppm([(-100.0, 14784.0)], seuil=200.0)
    assert geoms[0]["seg_left"] < 50.0  # min < 0
    assert geoms[0]["max_pos"] > 50.0  # max > 0


def test_domaine_partage_entre_candidats() -> None:
    """Les deux candidats partagent le même domaine → même 0 et même bande de tolérance."""
    geoms, dom = _echelle_ppm([(-100.0, 14784.0), (-7458.0, 7195.0)], seuil=200.0)
    assert geoms[0]["zero"] == geoms[1]["zero"]
    assert geoms[0]["tol_left"] == geoms[1]["tol_left"]
    assert geoms[0]["tol_width"] == geoms[1]["tol_width"]
    assert dom >= 14784  # le domaine couvre le pire écart


def test_domaine_arrondi_au_millier_superieur() -> None:
    """dom = millier supérieur du pire |écart| (14784 → 15000)."""
    _, dom = _echelle_ppm([(-100.0, 14784.0)], seuil=200.0)
    assert dom == 15000


def test_liste_vide_ne_plante_pas() -> None:
    """Aucun candidat (cas hors-profil) → liste vide, domaine non nul."""
    geoms, dom = _echelle_ppm([], seuil=200.0)
    assert geoms == []
    assert dom > 0


def test_seuil_nul_ne_contredit_pas_le_verdict() -> None:
    """seuil=0 (aucune tolérance définie) : rien n'est 'hors tolérance' et pas de
    facteur — sinon le rapport afficherait 'hors tolérance' ET 'dans la tolérance'."""
    geoms, _ = _echelle_ppm([(-100.0, 14784.0)], seuil=0.0)
    assert geoms[0]["hors_seuil"] is False
    assert geoms[0]["facteur"] is None
