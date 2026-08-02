# CRS Zone Toolkit — SPEC (cahier des charges fonctionnel V1)

> **Rôle du document.** Formaliser noir sur blanc ce que fait la V1, avec toutes les décisions ouvertes du document de définition **tranchées**. C'est le contrat fonctionnel : l'architecture technique (modules, signatures) se fera séparément, en s'appuyant sur ce document, `DATA_REFERENCE.md` (faits géodésiques), `feuille_de_route.md` (contraintes de scalabilité §1) et `references.md` (sources).
>
> **Version :** 0.1 · **Date :** 5 juillet 2026 · **Statut :** Brouillon — à valider avant `CLI_UX.md` et l'architecture

---

## 1. Identité

| Élément | Valeur |
|---|---|
| Dépôt GitHub | `crs-zone-toolkit` (public, licence MIT) |
| Package Python / PyPI | `crs-zone-toolkit` (import `crs_zone_toolkit`) |
| Commande CLI | `crszone` |
| Sous-commandes V1 | `analyze` · `apply` · `grid` |
| Profil de région V1 | `qc` (défaut ; option `--region` présente dès la V1, cf. feuille de route §1.3) |
| Python | ≥ 3.11 · Windows et Linux |
| Langue V1 | Interface et rapports en **français** (public cible : géomaticiens du Québec) ; toutes les chaînes regroupées dans un module unique pour l'i18n EN (V3, feuille de route §5) ; noms de sous-commandes et de flags en anglais (convention CLI) |

## 2. Problème adressé (rappel)

Choisir une projection métrique adaptée avant une analyse spatiale (buffers, surfaces, distances) au Québec : savoir dans quelles zones MTM tombent les données, mesurer la distorsion réellement encourue, décider entre zone MTM unique / Québec Lambert / découpage, puis exécuter la décision avec traçabilité. Prior art le plus proche : `estimate_utm_crs()` de GeoPandas — UTM seulement, pas de MTM/Lambert, pas de rapport, pas de multi-zones [REF-10].

## 3. Périmètre V1 / hors périmètre

**Inclus** : Québec (profil `qc`) ; couches vectorielles GeoPackage, Shapefile, GeoJSON ; les trois sous-commandes ; rapport HTML ; sortie `--json` ; journal de décision ; grille MTM committée.

**Exclu** (traçé en feuille de route) : autres régions, raster, plugin QGIS/toolbox ArcGIS, PDF (`--pdf`, V1.x), découpe géométrique exacte (`--split exact`, V1.x), changement de famille de datum à la demande (`--datum csrs`, V1.x), i18n EN.

---

## 4. `crszone analyze` — analyse et recommandation

### 4.1 Signature fonctionnelle

```
crszone analyze COUCHE [--region qc] [--assume-crs EPSG] [--report CHEMIN] [--json [CHEMIN]] [--quiet]
```

Entrée : une couche vectorielle. Sorties : résumé terminal (Rich), rapport HTML détaillé, optionnellement JSON structuré. **Aucune écriture de données géospatiales** — `analyze` est en lecture seule.

### 4.2 Étapes de l'analyse

1. **Identification du CRS d'entrée** : code EPSG, famille de datum (CSRS / NAD83 / NAD27 / WGS84 / autre), reconnaissance des CRS « en circulation » listés en `DATA_REFERENCE.md` §4.2 (MTQ Lambert, Québec Albers, SCoPQ zone 2…).
2. **CRS absent** : sans `--assume-crs`, l'analyse s'arrête avec un message expliquant les hypothèses plausibles (heuristique enrichie en V1.x) ; avec `--assume-crs`, l'hypothèse est tracée dans le rapport et le journal (« CRS supposé, non déclaré par la source »).
3. **Emprise et répartition par fuseau** : intersection des données avec la grille du profil (§6). La part par fuseau est mesurée sur la **grandeur dominante du type de géométrie** : surface (polygones), longueur (lignes), effectif (points).
4. **Distorsion mesurée** : échantillonnage de points sur les données (paramètre `n_echantillons`, défaut 200), plafonné et déterministe (aucun tirage aléatoire), méthode selon le type de géométrie dominant — points : chaque entité ; lignes : 3 fractions régulières par entité (0, 0,5, 1 de la longueur) ; polygones : le point représentatif de l'entité **plus** des points à fractions régulières de son contour (`boundary`, parties itérées pour un MultiPolygon, budget réparti au prorata de leur longueur), le contour portant les extrêmes de l'emprise où vit le max de distorsion. Pour chaque CRS candidat, facteurs d'échelle exacts via `pyproj.Proj.get_factors()` [REF-13] ; restitution min/moyenne/max en ppm. Le nombre de points réellement mesurés (`parametres.n_echantillons_effectif`, ≤ `n_echantillons`) est restitué en sortie (§8) — distinct du plafond demandé.
5. **Recommandation** selon la règle §4.3.
6. **Restitution** : résumé terminal + rapport HTML (§7) + JSON (§8).

### 4.3 Règle de décision (décision ouverte n°1 du doc de définition — tranchée)

Paramètres nommés, définis **dans le profil de région** :

| Paramètre | Défaut | Rôle |
|---|---|---|
| `distorsion_max_ppm` | 200 | Distorsion tolérée (max en valeur absolue sur l'échantillon) : sépare « fuseau sous tolérance » (`zone_dominante`) du cas « fuseau le moins déformé mais au-delà → découpage recommandé pour rester sous le seuil » (`zone_moins_deformee`). |
| `part_dominante_min` | 0,90 | *(amendé 2026-07-19)* **Ne gate plus la décision** — conservé au profil et en sortie JSON pour transparence (DT-16). Historique : part minimale pour recommander une zone unique. |

**Arbre de décision — « distorsion d'abord » (amendé 2026-07-19, calibrage §5 → `docs/calibrage/`)** :

1. **Un seul fuseau traversé** → recommander ce fuseau MTM (famille selon `DATA_REFERENCE.md` §1). Motif `mono_zone`.
2. **Plusieurs fuseaux** → recommander la **projection unique la moins déformée** entre le fuseau dominant et le Québec Lambert (le fuseau l'emporte à égalité : un fichier local vaut mieux que le Lambert provincial) :
   - fuseau dominant gagnant **et** distorsion ≤ `distorsion_max_ppm` → fuseau, motif `zone_dominante` ;
   - fuseau dominant gagnant mais distorsion > `distorsion_max_ppm` → fuseau, motif `zone_moins_deformee` (le découpage est mis en avant pour ramener chaque morceau sous le seuil — **seulement s'il produirait plusieurs fichiers**, cf. point 3) ;
   - Québec Lambert gagnant (données trop étendues — typiquement province entière ou grand nord) → Lambert (EPSG:6622 ou 32198 selon la famille), motif `lambert_moins_deforme`.
3. Le **découpage par fuseau** est présenté en alternative dès qu'il produirait **plusieurs fichiers** (n sorties, entités affectées par majorité), **jamais la recommandation automatique** : il est choisi explicitement par l'utilisateur.
   > **Amendé le 2026-08-02 (observations N20/N23).** La règle disait « dès qu'il y a plusieurs **fuseaux** » — c'est-à-dire plusieurs fuseaux *traversés*. Or l'affectation est **majoritaire** : une couche peut traverser trois fuseaux et n'en avoir qu'**un** de majoritaire, auquel cas le découpage rend **un seul** fichier — identique à une reprojection vers ce fuseau. **Mesuré sur la SDA : 12 régions multi-fuseaux sur 13** sont dans ce cas. Deux conséquences étaient fausses : l'alternative proposait une opération sans effet, et le motif `zone_moins_deformee` **affirmait** que le découpage « garde chaque morceau sous le seuil » alors qu'il n'aurait rien gardé du tout (Bas-Saint-Laurent : 407 ppm, un fichier). Le déclencheur devient donc « plusieurs fuseaux **majoritaires** » — ce que la parenthèse de cette règle disait déjà (« n sorties … par majorité »). **L'intention est intacte** : le découpage n'est jamais imposé, et reste offert chaque fois qu'il apporte quelque chose.
4. **Datum** : règles `DATA_REFERENCE.md` §1 (famille préservée ; CSRS par défaut si WGS84/indéfini ; NAD27 → cible CSRS avec transformation NTv2 signalée).
5. **Hors profil** : si une part des données tombe hors de la grille du profil (`qc`), l'analyse aboutit quand même et aucune recommandation n'est faite pour cette part ; `part_hors_profil` (§8) reste toujours exact. L'avertissement n'est **signalé qu'à partir de 1 %** (part affichée arrondie ≥ 1) : les échardes infimes liées à la limite simplifiée du profil (0,005°, cf. DATA_REFERENCE) ne déclenchent pas d'avertissement.

> **Pourquoi ce changement (2026-07-19).** L'ancien portillon « part dominante ≥ 0,90 → sinon Lambert » gatait *avant* la distorsion et envoyait au Lambert des régions compactes ou allongées dont le fuseau dominant était pourtant 10 à 25× moins déformé (ex. Bas-Saint-Laurent : MTM 6 = 407 ppm vs Lambert = 5106 ppm). Mesuré sur données réelles (SDA du Québec), le Lambert n'est la projection unique la moins déformée que pour les données province-entière ou grand-nord. La règle compare désormais directement les distorsions. Méthodologie et résultats : `docs/calibrage/2026-07-19-calibrage-seuils.md`.

Toute recommandation est accompagnée de sa **justification chiffrée** (parts par fuseau, distorsions comparées des candidats) — jamais un verdict sec.

---

## 5. `crszone apply` — reprojection / découpage

### 5.1 Signature fonctionnelle

```
crszone apply COUCHE [--region qc] [--choice zone|lambert|split] [--auto] [--out DOSSIER] [--format gpkg|geojson|shp] [--assume-crs EPSG] [--json [CHEMIN]]
```

### 5.2 Flux (analyser → décider → agir)

1. `apply` exécute l'analyse (§4) et affiche le résumé.
2. **Mode interactif (défaut)** : invite Rich proposant les options — appliquer la recommandation, choisir une alternative (zone précise / Lambert / découpage), ou annuler après lecture du rapport. Pas d'exécution silencieuse.
3. **Mode non interactif** : `--auto` applique la recommandation ; `--choice` impose une option sans invite. En environnement non interactif (pas de TTY) sans `--auto` ni `--choice`, l'outil s'arrête avec un message explicite (code de sortie 2).
4. Exécution : reprojection (pyproj/GeoPandas) ou découpage par **affectation majoritaire** (chaque entité va au fuseau où sa surface/longueur/position est dominante — décision actée, feuille de route §2 ; les entités restent intactes).
5. **Journal de décision** (§9) écrit dans le dossier de sortie.

### 5.3 Sorties

- Format par défaut : **GeoPackage**. Nommage : `<nom>_epsg<code>.<ext>` ; découpage : `<nom>_zone<n>_epsg<code>.<ext>` (une couche par fuseau non vide).
- Refus d'écraser un fichier existant sans `--overwrite`.
- Shapefile accepté en sortie mais accompagné d'un avertissement (limites du format : noms de champs tronqués, taille).

---

## 6. `crszone grid` — génération de la grille

```
crszone grid [--region qc] [--out CHEMIN] [--format geojson|gpkg] [--no-clip]
```

- Génère la grille des fuseaux du profil (bandes de longitudes de `DATA_REFERENCE.md` §2), **découpée sur la limite du Québec** par défaut (`--no-clip` pour les bandes complètes). Source de la limite administrative : **Découpages administratifs** du MRNF sur Données Québec, version 1/100 000, licence CC-BY 4.0 (attribution dans le README et dans les métadonnées de la grille) [REF-15].
- Attributs par cellule : `zone`, `epsg_csrs`, `epsg_nad83`, `epsg_nad27` (nullable), `meridien_central`, `lon_min`, `lon_max`.
- La grille committée dans le dépôt (`regions/qc/grille_mtm_qc.geojson`, embarquée dans le wheel — ARCHITECTURE A-05) est produite par cette commande — reproductible à l'identique (TP-32) ; c'est aussi la donnée de référence interne du moteur (détection §4.2.3).

---

## 7. Rapport HTML (décision ouverte n°2 — tranchée)

Un seul fichier **auto-porté** (template Jinja2, CSS inline, images en base64), contenant : identification de la couche et de son CRS (avec famille de datum et mentions spéciales — CRS supposé, MTQ Lambert détecté, NAD27…) ; **carte** (matplotlib : emprise des données superposée à la grille des fuseaux) ; tableau des parts par fuseau ; distorsions comparées des CRS candidats (min/moy/max ppm) ; recommandation et justification ; alternatives avec leurs conséquences ; rappel de la sémantique de découpage ; horodatage, version de l'outil, paramètres utilisés. Nommage : `<nom>_analyse_crs_<horodatage>.html` (horodatage `AAAAMMJJ-HHMMSS`, à côté de la couche, sauf `--report`) — chaque analyse produit un fichier unique, l'historique est conservé (amendé 2026-07-17).

**Rendu commutable clair/sombre (amendé 2026-07-17).** Le rapport propose un bouton de thème (soleil/lune) : il s'ouvre selon le réglage du système (`prefers-color-scheme`), **mémorise** le choix (`localStorage`), et **force le clair à l'impression**. C'est le **seul** JavaScript du rapport (~12 lignes inline, l'init du thème dans le `<head>` pour éviter tout flash ; aucune ressource externe — l'auto-portage reste l'invariant) ; sans JS, le rapport s'affiche en clair (dégradation lisible). La **carte** est rendue à fond transparent (palette neutre au thème) pour épouser les deux modes. La **distorsion** est présentée en **échelle divergente** centrée sur 0 ppm — bande de tolérance ±seuil, facteur de dépassement (≈ ×N) — plutôt qu'en simple table, et le verdict (cible recommandée) est mis en tête. Ces choix portent le rendu visuel, jamais la logique de recommandation (qui reste dans le moteur, ARCHITECTURE §2).

## 8. Sortie `--json`

Toutes les données du rapport sous forme structurée, pour scripts et pipelines : `schema_version` (dès la V1, feuille de route §1.5), couche, CRS d'entrée, famille, emprise, `zones_traversees[]` (zone, epsg, part), `distorsion{}` par candidat, `recommandation{}` (action, cible, motif), avertissements. Sur stdout par défaut (le résumé Rich passe alors sur stderr), ou vers un fichier si chemin fourni.

> **Valeurs de `recommandation.action`** (arrêtées au Jalon J2) : `"zone"` (fuseau MTM unique) · `"lambert"` (Québec Lambert) · `"aucune"` (100 % des données hors profil — aucune cible ; `cible_epsg = 0` **sentinelle**, `motif_code = "hors_profil"`). Les consommateurs (`apply`, rapport) **doivent tester `action` avant de lire `cible_epsg`** : `0` n'est pas un code EPSG valide. `motif_code` ∈ `{mono_zone, zone_dominante, zone_moins_deformee, lambert_moins_deforme, hors_profil}` *(amendé 2026-07-19, §4.3)*.

## 9. Journal de décision

Fichier JSON (`<nom>_journal.json`, `schema_version`) écrit par `apply` : analyse complète (§8), décision prise et **par qui** (interactif / `--auto` / `--choice`), pipeline de transformation PROJ réellement appliqué (`DATA_REFERENCE.md` §6.1), fichiers produits avec leur CRS final, horodatage et version. Le rapport HTML et le journal font foi pour la traçabilité — exigence du document de définition (§4.2).

## 10. Erreurs et codes de sortie

| Situation | Comportement | Code |
|---|---|---|
| Succès | — | 0 |
| Erreur d'exécution (fichier illisible, géométries invalides non réparables, écriture impossible) | Message clair, pas de trace brute en usage normal | 1 |
| Mauvais usage CLI (option inconnue, `apply` non interactif sans `--auto`/`--choice`, refus d'écraser) | Message + rappel `--help` | 2 |
| CRS absent sans `--assume-crs` | Message pédagogique (différence assigner/reprojeter [REF-11]) | 2 |
| Analyse aboutie avec avertissements (part hors profil, CRS supposé, NAD27) | Sortie normale, avertissements dans résumé/rapport/JSON | 0 |

Géométries invalides : tentative de réparation (`make_valid`) signalée en avertissement ; couche vide → erreur explicite (1). Aucun accès réseau requis à l'exécution (les grilles NTv2 pour NAD27 passent par proj-data ; si absentes, message expliquant comment les installer plutôt qu'un téléchargement silencieux).

## 11. Exigences non fonctionnelles

- **Qualité** (registre outillage §5.2) : TDD sur le moteur de décision ; cas du `TEST_PLAN.md` en tests pytest paramétrés ; CI GitHub Actions Ubuntu + Windows ; ruff + mypy ; couverture publiée.
- **Performance** : traitement en mémoire (GeoPandas) — suffisant V1 ; l'échantillonnage de distorsion est plafonné (`n_echantillons`), le coût ne croît pas avec la taille de la couche.
- **Scalabilité** : les six principes de `feuille_de_route.md` §1 sont des exigences de conception, vérifiées en revue (« est-ce que ce code survivrait à l'ajout du profil `ca` sans modification ? »).
- **API interne propre** : la CLI est une couche mince sur des fonctions importables (`analyze(...)`, `apply(...)`) — prépare l'API publique du backlog sans l'exposer encore.

## 12. Correspondance avec les décisions ouvertes du document de définition (§7)

| Décision ouverte | Résolution | Où |
|---|---|---|
| Seuil MTM unique vs Lambert | Règle « distorsion d'abord » (amendé 2026-07-19) : projection unique la moins déformée ; `distorsion_max_ppm` qualifie le découpage | SPEC §4.3 ; `docs/calibrage/` |
| Format du rapport | HTML auto-porté (txt et PDF écartés en V1) | SPEC §7 |
| Nom du package et sous-commandes | `crs-zone-toolkit` / `crszone` / `analyze`·`apply`·`grid` | SPEC §1 |
| Grille : statique ou à la volée | Committée + régénérable par `crszone grid` | SPEC §6 |
| CRS d'entrée non défini | Arrêt pédagogique + `--assume-crs` tracé | SPEC §4.2.2, §10 |
| *(ajoutée)* Sémantique multi-zones | Affectation majoritaire ; découpe exacte en V1.x | SPEC §5.2.4 |
| *(ajoutée)* Familles de datum | Règles `DATA_REFERENCE.md` §1 | SPEC §4.3.5 |

---

> *Prochaines étapes de cadrage : valider ce document, puis `CLI_UX.md` (maquette texte des flux §4–5) et `TEST_PLAN.md` (jeux de données calibrant §4.3). L'architecture technique vient ensuite.*
