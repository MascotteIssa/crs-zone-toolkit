# CRS Zone Toolkit — ARCHITECTURE

> **Rôle du document.** Dernier document de cadrage avant le code : style d'architecture, responsabilités par module, **lois de dépendance** (qui a le droit d'importer qui), API publique, modèle d'erreurs. La SPEC dit *quoi*, ce document dit *comment c'est découpé*. Toute dérogation se décide ici d'abord, pas dans le code.
>
> **Version :** 0.1 · **Date :** 6 juillet 2026 · **Statut :** Référence — à faire évoluer par amendements datés

---

## 1. Style : noyau fonctionnel + adaptateurs

Le principe hexagonal sans le cérémonial (décision du 2026-07-06, discutée en session de cadrage) :

- Un **noyau** (`core/`) de fonctions pures sur des GeoDataFrames : détection, distorsion, règles de décision, reprojection, génération de grille. Il ne connaît ni le terminal, ni le HTML, ni le Québec (les faits régionaux lui sont **injectés** via un `RegionProfile`).
- Des **adaptateurs minces** autour : la CLI (pilotant), le rapport HTML et le JSON (sortants), demain un plugin QGIS ou une toolbox ArcGIS (pilotants, cf. feuille de route — `arcpy`/`PyQGIS` resteraient confinés dans l'adaptateur).
- Pas d'interfaces abstraites ni d'injection de dépendances formelle : à cette échelle, la discipline d'imports (§3) suffit, et elle est **testée** (TP-40, TP-41).

Conséquence pour ArcGIS/QGIS (V1) : l'outil est un **standalone Python** ; l'interopérabilité passe par les fichiers (GPKG/SHP/GeoJSON) et les codes EPSG, lus identiquement par les deux SIG.

## 2. Modules et responsabilités

| Module | Responsabilité | Ne fait PAS |
|---|---|---|
| `cli.py` | Adaptateur Typer : parsing, invites Rich (CLI_UX), mapping exceptions → codes de sortie, routage `--json` stdout/stderr | Aucune logique métier, aucun calcul |
| `core/analysis.py` | Identification CRS/famille, répartition par fuseau, échantillonnage + `get_factors`, arbre de décision (SPEC §4.3) → `AnalysisResult` | Afficher, écrire des fichiers |
| `core/apply.py` | Reprojection, affectation majoritaire, écriture des sorties, journal de décision, inspection du pipeline PROJ (`TransformerGroup`) | Décider à la place de l'appelant (reçoit une `Decision`) |
| `core/gridgen.py` | Génération de la grille depuis le profil (bandes, découpe) | Connaître les valeurs du Québec |
| `core/report.py` | Adaptateur sortant : rendu HTML (Jinja2 + carte matplotlib) et JSON depuis `AnalysisResult`/`ApplyResult` | Toute logique de recommandation |
| `core/messages.py` | Toutes les chaînes utilisateur (FR), regroupées (i18n V3) | — |
| `core/profile.py` | Dataclasses gelées du profil (`RegionProfile`, `Fuseau`, `Seuils`) — la *forme* des données régionales, dans le noyau pour être importable sans dépendre de `regions/` | Contenir des valeurs régionales |
| `core/results.py` | Dataclasses gelées de résultat (`AnalysisResult`, `ZonePart`, `Distorsion`, `Recommandation`, `Emprise`) + `to_json()` (contrat SPEC §8) — feuille du noyau, importable par report/apply sans dépendre du moteur | Contenir de la logique de calcul |
| `core/targets.py` | Résolution des cibles EPSG (`target_family`, `fuseau_par_zone`, `zone_epsg`, `lambert_epsg`, `libelle_crs`) à partir du profil — partagé par `analysis` et `apply` | Contenir des valeurs régionales |
| `regions/loader.py` | Charge et **valide** `profil.toml` (→ `RegionProfile`) et l'emprise (`load_boundary`) ; lit les fichiers du profil | Définir la *forme* des données (c'est `core/profile.py`), interpréter les règles (c'est le noyau) |
| `regions/qc/` | Données du profil Québec : `profil.toml`, `grille_mtm_qc.geojson` | Contenir du code |
| `templates/` | `rapport.html.j2` (issu d'un gabarit visuel interne) | — |

**Convention de langue du code** : identifiants et noms de modules en anglais (portée internationale, feuille de route §5), docstrings et commentaires en français, chaînes utilisateur uniquement dans `messages.py`.

## 3. Lois de dépendance (testées par TP-40/TP-41)

```
cli.py ──────────► core/* , regions/loader        (+ typer, rich)
core/analysis|apply|gridgen ─► geopandas, shapely, pyproj, stdlib, core.profile, messages
core/report.py ──► jinja2, matplotlib, dataclasses de résultats
regions/loader.py ► tomllib, geopandas, core.errors, core.profile
```

`core.errors` et `core.profile` sont des **feuilles fondamentales** du noyau (types et exceptions, sans logique régionale) : `regions/loader` peut les importer. La direction interdite reste `core → regions` et `core → cli/adaptateurs`.

Interdits absolus :

1. Rien n'importe `cli.py`.
2. `core/analysis|apply|gridgen` n'importent **jamais** : typer, rich, jinja2, matplotlib.
3. **Aucun littéral EPSG québécois hors de `regions/qc/`** (TP-40). Le noyau reçoit un `RegionProfile`, point.
4. Le noyau ne lit aucun fichier de configuration lui-même (le loader le fait).
5. `arcpy` / `PyQGIS` : jamais, nulle part en V1 (futurs adaptateurs seulement).

## 4. API publique (contrat de la V1)

La CLI est un client de cette API comme un autre (SPEC §11). Signatures cibles :

```python
analyze(source: Path, *, region: str = "qc", assume_crs: str | None = None,
        n_samples: int | None = None) -> AnalysisResult

apply(source: Path, decision: Decision, *, region: str = "qc",
      out_dir: Path | None = None, out_format: str = "gpkg",
      overwrite: bool = False, assume_crs: str | None = None) -> ApplyResult

generate_grid(*, region: str = "qc", clip: bool = True) -> geopandas.GeoDataFrame
```

Types de résultats (dataclasses gelées, sérialisables) :

- `AnalysisResult` : couche, CRS d'entrée + famille de datum, emprise, `zones` (fuseau, EPSG, part), `distortion` par candidat (min/moy/max ppm), `recommendation` (action, cible, motifs), `warnings`, paramètres utilisés, `schema_version` ; `.to_json()` = contrat SPEC §8.
- `Decision` : choix (`recommendation` | `zone` | `lambert` | `split`), fuseau éventuel, origine (`interactive` | `auto` | `choice`).
- `ApplyResult` : fichiers produits (chemin + CRS final), pipeline PROJ appliqué, chemin du journal.

Le **journal** (SPEC §9) = `AnalysisResult` + `Decision` + `ApplyResult` sérialisés ensemble.

## 5. Modèle d'erreurs

Hiérarchie unique dans le noyau ; la CLI traduit (SPEC §10) — le noyau ne connaît pas les codes de sortie :

| Exception (base `CrsZoneError`) | Situation | Code CLI |
|---|---|---|
| `MissingCrsError` | CRS absent sans `assume_crs` | 2 |
| `OutputExistsError` | Sortie existante sans `overwrite` | 2 |
| `NonInteractiveError` | `apply` sans TTY ni `--auto`/`--choice` (levée par la CLI elle-même) | 2 |
| `EmptyLayerError` | Couche vide | 1 |
| `InvalidGeometryError` | Géométries irréparables (`make_valid` échoué) | 1 |
| `UnknownRegionError` | Profil inexistant ou invalide | 1 |
| `TransformUnavailableError` | Transformation de datum requise mais grille PROJ absente / pipeline « ballpark » seul | 1 |
| `LayerReadError` | Couche source illisible / introuvable | 1 |

Avertissements ≠ erreurs : portés par `AnalysisResult.warnings`, jamais levés (SPEC §10, dernier cas).

## 6. Flux de données

```
fichier ─► loader (RegionProfile) ─► analysis ─► AnalysisResult ─┬─► report.py ─► HTML / JSON
                                                                 ├─► cli.py (résumé Rich, invite)
                                                    Decision ────┴─► apply ─► fichiers + journal
```

`apply` réutilise l'`AnalysisResult` de la même exécution (pas de re-calcul entre l'invite et l'action).

## 7. Décisions d'architecture actées

| # | Décision | Motif | Référence |
|---|---|---|---|
| A-01 | Noyau fonctionnel + adaptateurs, sans formalisme hexagonal complet | Bénéfice/complexité à cette échelle | §1 |
| A-02 | Standalone pur en V1, pas d'environnements arcpy/QGIS | Interop par fichiers suffit ; fragilité conda/QGIS-Python | Feuille de route (backlog) |
| A-03 | Profil de région = TOML + GeoJSON (données), jamais du code | Feuille de route §1.2 ; V2 = un dossier de plus | TP-41 |
| A-04 | Code EN, docs/chaînes FR centralisées | Portée internationale + public QC | §2 |
| A-05 | `src layout`, grille embarquée dans le wheel | `pip install` livre un outil complet | Arborescence approuvée 2026-07-06 |
| A-06 | Dataclasses du profil (`RegionProfile`, `Fuseau`, `Seuils`) dans `core/profile.py`, pas dans `regions/loader.py` | Le noyau (gridgen/analysis/apply) reçoit un `RegionProfile` sans importer `regions/` (loi §3) ; le loader (regions) remplit ces types | §2, §3 (2026-07-06, J1) |
| A-07 | Emprise du Québec committée (`regions/qc/limite_qc.geojson`, simplifiée) et **injectée** dans `build_grid` | Le noyau ne lit aucun fichier (loi §3, loi 4) ; reproductibilité hors ligne de la grille (TP-32) | DATA_REFERENCE §6.2 (2026-07-06, J1) |

---

> *Ce document évolue par amendements datés dans la table §7. Si le code doit violer une loi du §3, on amende ici d'abord — sinon c'est le code qui a tort.*
