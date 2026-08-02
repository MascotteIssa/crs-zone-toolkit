# CRS Zone Toolkit — CLI_UX (maquette du flux terminal)

> **Rôle du document.** Maquette texte exacte de ce que l'utilisateur voit à chaque étape : résumés, invites, avertissements, erreurs. Sert de référence pour coder la couche interaction (Typer + Rich [REF-22][REF-23]) — l'expérience est calée **avant** d'écrire le code, conformément au flux « analyser → décider → agir » du document de définition (§5).
>
> Les valeurs chiffrées des maquettes sont **illustratives**. Les règles, noms de fichiers et codes de sortie font foi dans `SPEC.md`.
>
> **Version :** 0.1 · **Date :** 5 juillet 2026 · **Statut :** Brouillon — à valider avant le code d'interaction

---

## 1. Principes d'interface

1. **Résumé court, rapport complet** : le terminal donne juste assez pour décider ; le détail vit dans le rapport HTML (chemin toujours affiché).
2. **Jamais de verdict sec** : chaque recommandation est accompagnée de son motif chiffré sur une ligne.
3. **Symboles sobres** : `✓` (ok), `⚠` (avertissement), `✗` (erreur), `→` (recommandation). Couleurs Rich : vert/jaune/rouge/cyan respectivement — jamais porteuses d'information à elles seules (lisible sans couleur).
4. **Vocabulaire stable** : « fuseau » (pas « zone » seul), « famille de datum », « profil ». Les mêmes mots que dans le rapport HTML.
5. **stdout vs stderr** : avec `--json`, le JSON est seul sur stdout, tout l'affichage humain passe sur stderr (pipeline-safe).
6. Largeur cible 100 colonnes ; tout dégrade proprement à 80.
7. **Dégradation automatique hors TTY** : quand stdout n'est pas un terminal (pipe, redirection, CI), couleurs et barres sont désactivées automatiquement (comportement natif de Rich, à ne pas contourner) ; `--json` reste le format machine explicite.
8. **Flag vs sous-commande** : ce qui change l'*action* est une sous-commande (`analyze`/`apply`/`grid`) ; ce qui change le *comportement* est un flag (`--auto`, `--format`, `--no-clip`). Aucun modificateur ne devient une commande.

---

## 2. `crszone analyze` — cas nominal, fuseau unique

```
$ crszone analyze hydro_sherbrooke.gpkg

Analyse CRS — profil Québec (qc)                                    crszone 0.1.0
────────────────────────────────────────────────────────────────────────────────
Couche      hydro_sherbrooke.gpkg (1 842 entités, polygones)
CRS déclaré EPSG:4326 — WGS 84 (géographique)
Emprise     72,10°O → 71,64°O · 45,28°N → 45,52°N

Répartition par fuseau MTM (part de la surface totale)
  Fuseau 7 (MC −70,5°)  ████████████████████  100,0 %

Distorsion mesurée (200 points d'échantillonnage)
  Candidat                        min        moy        max
  MTM fuseau 7   EPSG:2949     −100 ppm    −64 ppm    −18 ppm
  Québec Lambert EPSG:6622      +41 ppm    +87 ppm   +132 ppm

→ Recommandation : reprojeter vers MTM fuseau 7 (EPSG:2949, NAD83(CSRS))
  Motif : Les données tiennent dans un seul fuseau (MTM 7).
  ⚠ Datum : entrée WGS 84 → famille CSRS par défaut.

✓ Rapport détaillé : hydro_sherbrooke_analyse_crs_20260728-130842.html
  Pour appliquer : crszone apply hydro_sherbrooke.gpkg
```

> *Amendé le 2026-08-01 (DT-20 **(2)**, DT-26) : le nom du rapport porte un **horodatage** — deux analyses successives ne s'écrasent plus, l'historique est conservé ; c'est le code qui l'emporte. La ligne Datum reçoit un **⚠** parce que la famille **change** (WGS 84 → CSRS, ≈ 1 m au Québec) : le marqueur signale désormais ce qui bouge, jamais ce qui reste.*
>
> *Amendé le 2026-07-28 : titre de répartition complété par la grandeur mesurée, par cohérence avec l'écran §3 — le code (Task 3) affiche désormais toujours cette grandeur. Couche illustrée en polygones : la grandeur est la surface, pas l'effectif (SPEC §4.2.3, `analyse_repartition_titre` / `_REPARTITION_GRANDEUR` dans `core/messages.py`). Ligne Motif également amendée : elle décrivait une règle chiffrée (part / seuil) absente du gabarit réel `motif_mono_zone` — les chaînes `motif_*` sont protégées (partagées avec le rapport HTML validé le 17/07), c'est la maquette qui cède, comme en §3.*

Code de sortie : 0.

---

## 3. `crszone analyze` — cas multi-fuseaux (recommandation Lambert)

```
$ crszone analyze routes_laurentides_outaouais.gpkg

Analyse CRS — profil Québec (qc)                                    crszone 0.1.0
────────────────────────────────────────────────────────────────────────────────
Couche      routes_laurentides_outaouais.gpkg (12 507 entités, lignes)
CRS déclaré EPSG:4269 — NAD83 (géographique)
Emprise     77,35°O → 73,90°O · 45,45°N → 47,10°N

Répartition par fuseau MTM (part de la longueur totale)
  Fuseau 9 (MC −76,5°)  ████████████          58,3 %
  Fuseau 8 (MC −73,5°)  ████████              41,7 %

Distorsion mesurée (200 points d'échantillonnage)
  Candidat                            min        moy        max
  MTM fuseau 9 (tout) EPSG:32189   −100 ppm    +96 ppm   +471 ppm  ⚠ hors seuil
  Québec Lambert      EPSG:32198    +38 ppm   +102 ppm   +169 ppm

→ Recommandation : reprojeter vers Québec Lambert (EPSG:32198, NAD83)
  Motif : Les données sont trop étendues pour le fuseau dominant (MTM 9 : 471 ppm) : le Québec Lambert est la projection unique la moins déformée (169 ppm max). Découpage disponible en alternative.
  ✓ Datum : entrée NAD83 d'origine → famille préservée (EPSG:32198).
    Entrée en NAD83 d'origine : la famille est préservée (pas de changement de
    datum silencieux). Note : NAD83(CSRS) est le standard actuel.

  Alternative : découpage par fuseau (2 sorties, entités affectées au fuseau majoritaire).

✓ Rapport détaillé : routes_laurentides_outaouais_analyse_crs_20260728-130842.html
  Pour appliquer : crszone apply routes_laurentides_outaouais.gpkg
```

> *Amendé le 2026-08-01 (DT-20 **(2) (3)**, DT-26, DT-29) : ① le nom du rapport est **horodaté** (divergence (2), le code l'emporte) ; ② l'avertissement CSRS devient une **note neutre**, dans la formulation du code — divergence (3), arbitrée « la maquette s'aligne » : cette chaîne transitait par le JSON et le rapport HTML validé le 17/07, la changer avait un coût de contrat. Elle **perd son ⚠** (DT-26 : le marqueur va au changement de famille, pas à la préservation) et reçoit un **retrait de continuation** (DT-29, N18) ; ③ le tableau sépare le libellé du code EPSG par **un** espace, comme le code — la largeur des colonnes est calculée sur le contenu réel. **Reste ouvert : N21**, la note répète la ligne qu'elle accompagne.*
>
> *Amendé le 2026-07-28 : la ligne « Motif » de cette maquette décrivait la règle `part_dominante_min` abandonnée au calibrage du 2026-07-19 (SPEC §4.3, `docs/calibrage/`). Elle reflète désormais la règle « distorsion d'abord » : on recommande la projection unique la moins déformée, le découpage restant offert en alternative.*

Code de sortie : 0 (l'avertissement datum n'est pas bloquant, cf. `SPEC.md` §10).

---

## 4. `crszone apply` — mode interactif (défaut)

Reprend l'affichage de l'analyse (§3) — **sans** la ligne « Pour appliquer », qui n'a pas de sens ici (DT-29, N2) — puis :

```

Que voulez-vous faire ?
  [1] Appliquer la recommandation — Québec Lambert (EPSG:32198)
  [2] Reprojeter vers un fuseau MTM unique (préciser : 8 ou 9)
  [3] Découper par fuseau MTM — affectation majoritaire, 2 sorties
  [0] Annuler (relire le rapport avant de décider)

Votre choix [1] : 1

✓ Sortie   : sorties/routes_laurentides_outaouais_epsg32198.gpkg
✓ Journal  : sorties/routes_laurentides_outaouais_journal.json
  Pipeline PROJ : « Inverse of NAD83 to WGS 84 + Quebec Lambert » (aucune transformation de datum)
```

> *Amendé le 2026-08-02 (observation N22) : cette maquette montrait, entre le choix et les
> sorties, une ligne de progression — `Reprojection vers EPSG:32198…  ✓ terminé (12 507 entités,
> 3,4 s)`. **Elle n'a jamais été implémentée** et ne l'est pas : l'exécution passe directement
> aux `✓ Sortie`. Décision : **ne pas l'ajouter en V1.** Les durées en jeu (3 à 9 s sur les plus
> grosses couches mesurées) sont inconfortables, pas bloquantes ; et une animation rendrait la
> sortie **non déterministe**, donc les blocs console du README non régénérables — l'idempotence
> qu'on vient d'obtenir (DT-17) serait perdue. Si le besoin se confirme, le bon compromis est une
> ligne **statique** avant l'exécution, sans animation. La maquette cède ; l'intention est
> consignée au registre.*

- Choix `[2]` → sous-invite « Quel fuseau ? [9] : » (le dominant en défaut), avec rappel `⚠ distorsion max +471 ppm hors seuil` si l'utilisateur choisit un fuseau au-delà du seuil. **Aucune confirmation supplémentaire n'est demandée** — choisir `[2]` puis saisir un numéro de fuseau **est déjà** l'acte conscient ; une invite de plus ajouterait de la friction sans information *(amendé le 2026-08-01, observation N5 — la maquette cède sur ce point)*. Le choix est en revanche **journalisé** : `decision.note` porte « choix utilisateur ≠ recommandation » *(DT-27 — la trace, elle, est bien due)*.
- Choix `[0]` → « Analyse conservée, aucune donnée écrite. **Rapport à relire : `<couche>_analyse_crs_<horodatage>.html`.** Relancez crszone apply quand vous aurez décidé. » — code de sortie 0. *(Amendé le 2026-08-01, DT-23 : `apply` **écrit** désormais le rapport, avant d'afficher le menu — sans quoi « relire le rapport avant de décider » était une promesse creuse. Le message le nomme, sinon on saurait qu'il existe sans savoir où.)*
- Entrée vide → défaut `[1]`.

## 5. `crszone apply --auto` et non-interactif

```
$ crszone apply routes_laurentides_outaouais.gpkg --auto --out sorties/
[analyse §3 abrégée : en-tête + version, filet, Couche, CRS déclaré, Emprise, puis
 Recommandation / Motif / Datum — sans les blocs Répartition et Distorsion,
 et sans la ligne « Pour appliquer »]
Mode --auto : application de la recommandation (Québec Lambert, EPSG:32198).
✓ Sortie   : sorties/routes_laurentides_outaouais_epsg32198.gpkg
✓ Journal  : sorties/routes_laurentides_outaouais_journal.json
```

> *Amendé le 2026-08-01 (DT-20 **(4)**, DT-29) : la maquette décrivait le mode abrégé comme « lignes Couche / Recommandation / Motif seulement », alors qu'il affiche aussi l'en-tête, la version, le filet, le CRS déclaré, l'Emprise et le Datum. Divergence préexistante, aggravée de deux lignes par la Phase B sans que ce paragraphe soit relu : c'est la maquette qui cède. La ligne « Pour appliquer » en est retirée (N2), et `--auto` écrit **aucun** rapport — le périmètre de DT-23 s'arrête au mode interactif et à `--choice split`.*

Sans TTY et sans `--auto`/`--choice` :

```
✗ Session non interactive : impossible de demander une confirmation.
  Utilisez --auto (appliquer la recommandation) ou --choice zone|lambert|split.
```

Code de sortie : 2.

---

## 6. Cas d'erreur et d'avertissement

### 6.1 CRS absent (sans `--assume-crs`) — sortie 2

```
✗ La couche parcelles.shp ne déclare aucun CRS (.prj absent).

  Impossible d'analyser sans connaître le système d'origine : assigner un CRS
  n'est pas reprojeter — se tromper d'hypothèse fausserait toutes les mesures.

  Si vous connaissez le CRS d'origine :
      crszone analyze parcelles.shp --assume-crs EPSG:2950
  Indices dans le rapport de plausibilité à venir (V1.x). Voir aussi le rapport
  HTML d'une couche voisine, ou la documentation de la source de données.
```

### 6.2 Hypothèse `--assume-crs` — bandeau permanent

```
⚠ CRS SUPPOSÉ : EPSG:2950 fourni par --assume-crs, non déclaré par la source.
  L'hypothèse est tracée dans le rapport et le journal.
```

### 6.3 Entrée NAD27 — avertissement + transformation explicite

```
⚠ Datum historique NAD27 détecté (EPSG:32084 — MTM fuseau 4).
  La cible recommandée est en NAD83(CSRS) : une transformation de datum sera
  appliquée via la grille NTv2 officielle (écarts NAD27→CSRS : dizaines de mètres).
  Le pipeline exact sera journalisé.
```

Si la grille NTv2 est absente de l'installation PROJ : erreur (sortie 1) expliquant comment l'installer (`proj-data` / `projsync`), **jamais** de transformation approximative silencieuse ni de téléchargement automatique.

### 6.4 Données partiellement hors profil

```
⚠ 12,4 % des données (surface) hors de la grille du profil qc (au sud de la
  frontière, État de New York). Aucune recommandation pour cette part — détail
  dans le rapport, section Couverture.
```

### 6.5 Refus d'écraser — sortie 2

```
✗ sorties/routes_epsg32198.gpkg existe déjà. Utilisez --overwrite pour remplacer.
```

---

## 7. `crszone grid`

```
$ crszone grid --out grille_mtm_qc.geojson

Grille des fuseaux MTM — profil Québec (qc)
  9 fuseaux (2 à 10) · bandes de 3° · découpe : limite du Québec (SDA MRNF, CC-BY 4.0)
✓ grille_mtm_qc.geojson (9 entités, attributs : zone, epsg_csrs, epsg_nad83,
  epsg_nad27, meridien_central, lon_min, lon_max)
```

`--no-clip` remplace la ligne « découpe » par « bandes complètes (57°O → 81°O, non découpées) ».

---

## 8. `--json` / `--json-out` (analyze et apply)

`--json` (booléen) : le JSON est **seul** sur stdout, tout l'affichage humain passe sur stderr.

```
$ crszone analyze routes.gpkg --json > analyse.json
[résumé humain des §2–3 affiché sur stderr]
$ cat analyse.json   # → objet JSON de SPEC.md §8, schema_version en tête
```

`--json-out CHEMIN` (fichier) : écrit le JSON dans `CHEMIN` et garde l'affichage humain sur stdout.

```
$ crszone analyze routes.gpkg --json-out analyse.json
[résumé humain des §2–3 affiché sur stdout]
$ cat analyse.json   # → même objet JSON
```

> **Note :** typer 0.26 ne supporte pas d'option à valeur optionnelle ; `--json chemin` est
> remplacé par `--json-out chemin` (arbitrage J5, cf. design §8).

> **Amendement du 2026-08-01 (DT-30).** Le premier exemple ci-dessus (`--json > analyse.json`)
> est le geste naturel — et, sous PowerShell, le mauvais : la redirection décode la sortie avec
> `[Console]::OutputEncoding` puis la réécrit en UTF-16LE, produisant un fichier corrompu alors
> que l'outil a bien émis de l'UTF-8. **`--json-out` est le chemin à recommander sur Windows**,
> et c'est celui que la documentation met désormais en avant.

---

## 9. `--help` (extrait de ton)

```
$ crszone --help
crszone — analyse, recommandation et reprojection CRS pour le Québec (MTM / Lambert)

Commandes :
  analyze  Analyser une couche : fuseaux traversés, distorsion, recommandation (lecture seule)
  apply    Reprojeter ou découper après confirmation (analyser → décider → agir)
  grid     Générer la grille des fuseaux MTM du profil

Options globales : --region (défaut : qc) · --version · --help
```

---

> *Maquette de référence. Tout écart entre le code d'interaction et ce document doit être arbitré (mettre à jour l'un ou l'autre, pas laisser dériver). Les chaînes affichées ici seront centralisées dans un module unique dès la V1 (i18n, feuille de route §5).*
