"""Affectation majoritaire d'une entité à un fuseau — source de vérité unique.

Le découpage (SPEC §5) affecte **chaque entité intacte** au fuseau dont le
recouvrement est dominant : une entité à cheval ne va donc que dans **un** seul
fichier. Deux modules ont besoin de ce fait, pour des raisons différentes :

- `core.apply` l'applique, pour écrire les fichiers ;
- `core.analysis` l'anticipe, pour **annoncer le nombre de sorties** avant que
  l'utilisateur décide (DT-25).

Ils doivent répondre exactement la même chose. Les faire calculer chacun de son
côté serait reproduire le défaut de DT-19 (listes parallèles qui dérivent) sur
un chemin bien plus coûteux : l'annonce et la réalité divergeraient en silence,
ce qui est précisément le bug qu'on corrige ici. D'où ce module, dont les deux
dépendent sans dépendre l'un de l'autre — même motif que `core.targets`.
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry.base import BaseGeometry


def mesure_recouvrement(geom: BaseGeometry, cellule: BaseGeometry) -> float:
    """Grandeur dominante de l'intersection selon le type : surface / longueur / point."""
    inter = geom.intersection(cellule)
    if inter.is_empty:
        return 0.0
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return float(inter.area)
    if geom.geom_type in ("LineString", "MultiLineString"):
        return float(inter.length)
    return 1.0  # point(s) : présence dans la cellule


def zone_par_entite(data: gpd.GeoDataFrame, cells: gpd.GeoDataFrame) -> list[tuple[int, bool]]:
    """Fuseau dominant de chaque entité, dans l'ordre de `data`.

    Renvoie `(zone, par_repli)` par entité. `par_repli` est vrai quand l'entité
    ne recouvre **aucune** cellule (100 % hors profil) et se voit affectée au
    fuseau le plus proche de son centroïde — l'appelant décide s'il en avertit.

    `data` et `cells` doivent déjà être dans la **même projection métrique** :
    comparer des surfaces en degrés fausserait la majorité (D-J2-6).

    **Mesuré seulement où c'est nécessaire.** Un `sjoin` (indexé) donne d'abord
    les cellules *candidates* de chaque entité ; l'écrasante majorité des entités
    n'en touche qu'une — leur fuseau est connu sans aucun calcul d'intersection.
    Seules celles à cheval sont mesurées, et seulement contre leurs candidates.
    La boucle naïve « chaque entité × chaque cellule » coûtait, sur 12 580 lignes
    et 9 fuseaux, 113 000 intersections shapely, dont plus de 99 % rendaient zéro.

    Le résultat est identique : une cellule qui n'intersecte pas rend une mesure
    nulle et n'aurait jamais été retenue. L'ordre des candidates est celui de
    `cells`, donc le départage d'une égalité exacte est inchangé (DT-09).
    """
    candidates = _cellules_candidates(data, cells)
    zones = cells["zone"].astype(int).to_numpy()
    geometries = cells.geometry.to_numpy()

    resultat: list[tuple[int, bool]] = []
    for position, geom in enumerate(data.geometry):
        indices = candidates.get(position, ())
        meilleure_zone: int | None = None
        meilleure_mesure = 0.0
        if len(indices) == 1:  # cas dominant : une seule cellule touchée
            meilleure_zone = int(zones[indices[0]])
        else:
            for i in indices:
                m = mesure_recouvrement(geom, geometries[i])
                if m > meilleure_mesure:
                    meilleure_mesure = m
                    meilleure_zone = int(zones[i])
        if meilleure_zone is None:  # aucune candidate, ou recouvrement nul partout
            distances = cells.geometry.distance(geom.centroid)
            resultat.append((int(cells.loc[distances.idxmin(), "zone"]), True))
        else:
            resultat.append((meilleure_zone, False))
    return resultat


def _cellules_candidates(
    data: gpd.GeoDataFrame, cells: gpd.GeoDataFrame
) -> dict[int, tuple[int, ...]]:
    """Indices positionnels des cellules intersectant chaque entité, par position."""
    gauche = data.geometry.reset_index(drop=True).to_frame("geometry")
    droite = cells.geometry.reset_index(drop=True).to_frame("geometry")
    joint = gpd.sjoin(gauche, droite, predicate="intersects", how="inner")
    par_entite: dict[int, list[int]] = {}
    for position, cellule in zip(joint.index, joint["index_right"], strict=True):
        par_entite.setdefault(int(position), []).append(int(cellule))
    return {k: tuple(sorted(v)) for k, v in par_entite.items()}


def zones_majoritaires(
    gdf: gpd.GeoDataFrame, grid: gpd.GeoDataFrame, measure_crs: int
) -> list[int]:
    """Fuseaux qui recevraient au moins une entité — donc le nombre de **fichiers**.

    À ne pas confondre avec les fuseaux **traversés** : c'est toute la question
    de DT-25. Une couche peut traverser neuf fuseaux et n'en produire que six.
    """
    zones = zone_par_entite(gdf.to_crs(measure_crs), grid.to_crs(measure_crs))
    return sorted({zone for zone, _ in zones})
