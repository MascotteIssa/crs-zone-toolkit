# CRS Zone Toolkit — TEST_PLAN (jeux de test et calibrage des seuils)

> **Rôle du document.** Définir les jeux de données de test et les résultats attendus qui (1) valident objectivement chaque règle de `SPEC.md` et `DATA_REFERENCE.md`, (2) **calibrent** les deux seuils de la règle de décision (`part_dominante_min`, `distorsion_max_ppm`), (3) alimentent directement les tests pytest (TDD : ces cas s'écrivent **avant** le code du moteur).
>
> **Version :** 0.1 · **Date :** 5 juillet 2026 · **Statut :** Brouillon — à valider avant l'architecture
>
> **Principes.**
> 1. **Tout jeu de test est généré par code** (fixtures `conftest.py`, Shapely + GeoPandas) — aucun binaire committé. Reproductible, léger, et les coordonnées sont choisies exprès pour la règle testée.
> 2. Chaque cas porte un ID stable (`TP-xx`), la règle qu'il valide (renvoi SPEC/DATA_REFERENCE), et son résultat attendu **vérifiable sur la sortie `--json`** (pas sur le texte du terminal, qui peut évoluer).
> 3. Repères géographiques utilisés : Sherbrooke ≈ 71,9°O (fuseau 7) · frontière fuseaux 8/9 = 75°O · Gatineau ≈ 75,7°O (fuseau 9) · Montréal ≈ 73,6°O (fuseau 8).

---

## 1. Détection et recommandation (`analyze`)

| ID | Jeu généré | Construction | Résultat attendu | Valide |
|---|---|---|---|---|
| TP-01 | Points mono-fuseau | 50 points aléatoires dans bbox 72°O–71,5°O × 45,3–45,6°N, CRS 4326 | Rec = MTM fuseau 7, **EPSG:2949** (CSRS car entrée WGS84) ; 100 % fuseau 7 ; exit 0 | SPEC §4.3.1, §4.3.5 ; DATA_REF §1.3 |
| TP-02 | Lignes 2 fuseaux, dominant ~58 % | Lignes traversant 75°O, ~58 % de longueur côté fuseau 9 | *(B2, 2026-07-19)* Rec = **fuseau MTM 9 (CSRS 2951)**, motif `zone_moins_deformee` (fuseau le moins déformé mais > tolérance) ; parts ≈ 58/42 (±2 pts) ; découpage en alternative | SPEC §4.3 |
| TP-03 | Polygones 3+ fuseaux | Bande est-ouest 78,5°O → 70°O (fuseaux 7-8-9-10) | Rec = Québec Lambert, motif `lambert_moins_deforme` (le fuseau dominant se déforme plus que le Lambert) ; 4 fuseaux ; découpage en alternative | SPEC §4.3 |
| TP-04 | Dominant fort, distorsion OK | 95 % des points dans le fuseau 8, 5 % juste au-delà de 75°O | Rec = **fuseau dominant 8** (le moins déformé et ≤ seuil), motif `zone_dominante` ; découpage en alternative | SPEC §4.3 |
| TP-05 | Dominant fort, très étalé | 91 % dans le fuseau 8 par effectif, mais points minoritaires très à l'ouest (≥ 77,5°O) → le fuseau se déforme plus que le Lambert | *(B2)* Rec = Québec Lambert, motif `lambert_moins_deforme` | SPEC §4.3 — règle « distorsion d'abord » |
| TP-06 | Sans CRS | Shapefile écrit puis `.prj` supprimé | Sans `--assume-crs` : exit 2, aucun rapport ; avec `--assume-crs EPSG:2950` : analyse OK + avertissement « CRS supposé » dans le JSON | SPEC §4.2.2, §10 |
| TP-07 | Entrée vieux NAD83 | TP-02 réécrit en EPSG:4269 | Rec = **32189** (MTM 9 NAD83 — TP-02 recommande le fuseau sous B2 ; famille préservée, pas 2951) + note « CSRS standard actuel » | DATA_REF §1.2 |
| TP-08 | Entrée NAD27 | Points fuseau 4 en EPSG:32084 | Rec = cible CSRS + avertissement transformation NTv2 ; si grille PROJ absente à l'`apply` : exit 1 avec message d'installation | DATA_REF §1.5, §6.1 |
| TP-09 | Entrée SCoPQ zone 2 | Points en EPSG:2944 | Reconnu équivalent fuseau 2 (pas « CRS inconnu ») ; note explicative | DATA_REF §2 (piège fuseau 2) |
| TP-10 | Entrée MTQ Lambert | Points en EPSG:3798 | Identifié « MTQ Lambert » et **distingué** du Québec Lambert dans le JSON | DATA_REF §4.2 |
| TP-11 | Partiellement hors profil | 85 % Québec (fuseau 9), 15 % côté Ontario (au-delà de la limite de la grille découpée) | Exit 0 ; avertissement « x % hors profil qc » avec x ≈ 15 | SPEC §4.3.6 |
| TP-12 | Couche vide | GeoDataFrame 0 entité | Exit 1, message explicite | SPEC §10 |
| TP-13 | Géométries invalides | Polygone papillon (auto-intersection) réparable | `make_valid` appliqué + avertissement ; analyse aboutit | SPEC §10 |

## 2. Reprojection et découpage (`apply`)

| ID | Jeu | Construction | Résultat attendu | Valide |
|---|---|---|---|---|
| TP-20 | Reprojection simple | TP-01 + `--auto` | Fichier `<nom>_epsg2949.gpkg`, CRS de sortie 2949, effectif conservé, journal présent | SPEC §5.2–5.3 |
| TP-21 | Découpage 2 fuseaux | TP-02 + `--choice split` | 2 fichiers `_zone8_`/`_zone9_` ; **somme des entités = total d'origine, aucune dupliquée ni coupée** | SPEC §5.2.4, §5.3 |
| TP-22 | **Majorité ≠ centroïde** | Polygone en croissant à cheval sur 75°O : surface majoritaire fuseau 8, **centroïde dans le fuseau 9** | Affecté au fuseau **8** (majorité surfacique) — le test qui verrouille la sémantique choisie | SPEC §5.2.4 ; décision feuille de route §2 |
| TP-23 | Ligne majoritaire | Ligne dont 70 % de la longueur est en fuseau 9 | Affectée au fuseau 9 (majorité par longueur pour les lignes) | SPEC §4.2.3, §5.2.4 |
| TP-24 | Refus d'écraser | Relancer TP-20 sans `--overwrite` puis avec | Exit 2 puis succès | SPEC §5.3 |
| TP-25 | Non-interactif nu | TP-02 sans TTY, sans `--auto`/`--choice` | Exit 2, message CLI_UX §5 | SPEC §5.2.3 |
| TP-26 | Choix contre recommandation | TP-02 + `--choice lambert` (la reco B2 étant le fuseau 9) | Exécuté ; journal note « choix utilisateur ≠ recommandation » | SPEC §9 ; CLI_UX §4 |
| TP-27 | Journal complet | TP-20 | JSON valide : `schema_version`, analyse, décision + mode (auto/choice/interactif), **pipeline PROJ**, fichiers produits + CRS final | SPEC §9 ; DATA_REF §6.1 |

## 3. Grille et sorties machine

| ID | Cas | Résultat attendu | Valide |
|---|---|---|---|
| TP-30 | `grid` par défaut | 9 entités ; attributs complets ; `epsg_nad27` non nul pour fuseaux 2–6 seulement ; géométries découpées ⊂ bandes complètes | SPEC §6 ; DATA_REF §2 |
| TP-31 | `grid --no-clip` | Bandes rectangulaires complètes ; la version découpée est incluse dans la non-découpée | SPEC §6 |
| TP-32 | Grille committée = grille générée | Régénérer et comparer à `regions/qc/grille_mtm_qc.geojson` (géométries + attributs identiques) | SPEC §6 — test anti-dérive |
| TP-33 | `--json` | Sortie = JSON seul sur stdout, parsable, `schema_version` présent, validée contre un schéma JSON versionné dans `tests/` | SPEC §8 ; feuille de route §1.5 |

## 4. Non-régression « scalabilité » (feuille de route §1)

| ID | Cas | Résultat attendu |
|---|---|---|
| TP-40 | **Aucun fait géodésique en dur dans le moteur** : test qui balaie `src/crs_zone_toolkit/core/` et échoue si un code EPSG québécois (2944…2952, 3218x, 6622, 32198…) y apparaît en littéral | Les codes ne vivent que dans `regions/qc/profil.toml` |
| TP-41 | **Profil factice** : profil de test `zz` (2 fuseaux fictifs, grille minuscule, seuils exotiques) chargé par le moteur | Analyse et apply fonctionnent sans aucune modification du moteur — preuve avant l'heure que le profil `ca` (V2) sera indolore |

## 5. Calibrage des seuils (SPEC §4.3 — à exécuter une fois le moteur testable)

Les défauts (`part_dominante_min` = 0,90 ; `distorsion_max_ppm` = 200) sont des hypothèses. Protocole de calibrage :

1. **Famille paramétrique de jeux** : générer des couches en balayant la part dominante (0,70 → 0,99 par pas de 0,05) × l'étalement est-ouest (0,5° → 4°) × 2 latitudes (46°N, 52°N).
2. Pour chaque couche : recommandation obtenue vs jugement attendu (grille d'expertise remplie à la main dans un tableau annexe — c'est le juge, pas l'outil).
3. Retenir le couple de seuils qui minimise les recommandations contre-intuitives ; en cas d'ex æquo, préférer le plus conservateur (celui qui envoie plus tôt vers Lambert).
4. **Documenter** : valeurs retenues + tableau de calibrage → mise à jour de `profil.toml`, de `SPEC.md` §4.3 et une note ici. Repères théoriques à confronter aux mesures `get_factors()` [REF-13] : MTM en bande ≈ −100 à +60 ppm (~47°N) ; ~+470 ppm à 3° du méridien central.

## 6. Validation manuelle sur données réelles (non committées, hors CI)

Avant chaque release : télécharger 2 jeux ouverts de Données Québec — dont **Découpages administratifs** 1/100 000 [REF-15] (multi-fuseaux garanti) et un jeu local mono-fuseau — et vérifier : recommandations plausibles, rapport HTML lisible, cartes correctes, temps de traitement raisonnable. Résultats consignés dans la PR de release (pas dans le dépôt).

## 7. Outillage

pytest + pytest-cov (registre outillage §5.2) ; cas TP en `@pytest.mark.parametrize` quand ils partagent une mécanique ; assertions sur `--json` et les fichiers produits, jamais sur le texte terminal ; CI Ubuntu + Windows (TP-06 et TP-25 sont sensibles à l'OS — suppression de `.prj`, absence de TTY). `hypothesis` (tests par propriétés : « toute couche mono-fuseau doit recevoir une rec mono-fuseau ») envisagé en V1.x, pas en V1.

**Exception bornée — tests dorés de maquette CLI (2026-07-28, périmètre à jour 2026-07-28 Phase C).** La règle « assertions sur le JSON et les fichiers produits, jamais sur le texte terminal » reste la règle du **moteur**. Elle laissait toutefois la couche de présentation sans filet, ce qui a produit DT-02 puis son résidu DT-14. On autorise donc **un test doré par écran de `CLI_UX.md`** — aujourd'hui **quatre** : §2 (`analyze` mono-fuseau), §3 (`analyze` multi-fuseaux), §4 (`apply` interactif, résumé complet sans rapport) et §5 (`apply --auto`/`--choice`, résumé abrégé) — vérifié sur la sortie d'une console Rich à **largeur fixe, sans couleur**, selon un **style unique** d'assertion : quelques `==` ciblés sur des lignes individuelles précises, complétés par des assertions structurelles (`startswith`, `endswith`, `any`, `next` — préfixe de ligne, présence/absence d'une section, position relative) pour le reste ; aucun ne compare un bloc entier attendu. Ces tests vivent dans `tests/test_affichage_maquette.py`, sont nommément identifiés, et sont les **seuls** autorisés à asserter du texte terminal. Toute divergence qu'ils révèlent s'arbitre comme d'habitude : soit le code rejoint la maquette, soit la maquette est amendée — jamais le test assoupli.

---

> *Ces cas s'écrivent en tests AVANT le code du moteur (TDD). Un cas qui ne peut pas s'exprimer en assertion sur le JSON ou les fichiers produits est un signe que la SPEC manque de précision — corriger la SPEC, pas le test.*
