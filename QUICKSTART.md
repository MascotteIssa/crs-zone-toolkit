# crszone : démarrage rapide

`crszone` analyse une couche vectorielle, recommande un système de coordonnées
adapté au Québec (fuseau MTM ou Québec Lambert) et reprojette la couche sur demande.
L’outil recommande ; vous décidez (rien n’est reprojeté sans votre accord).

> Les exemples ci-dessous s’exécutent depuis un terminal (l’interface en ligne de
> commande de votre système), avec le préfixe `uv run` propre à l’environnement de
> développement du projet. Après installation normale du paquet, la commande s’appelle
> directement `crszone`, sans ce préfixe.
>
> Si le terminal ne vous est pas familier, la commande `crszone-gui` ouvre une fenêtre qui
> mène les mêmes opérations sans en écrire aucune (elle s’installe avec le paquet). Ses
> deux parcours, « Traiter une couche » et « Générer la grille des fuseaux », appellent le
> même moteur que les commandes décrites ici.

## Les trois commandes

### 1. Analyser une couche, en lecture seule : que faire de vos données ?

```bash
uv run crszone analyze chemin/vers/couche.gpkg
```

La commande affiche le CRS déclaré, l’emprise, la répartition par fuseau MTM, la
distorsion des candidats et une recommandation chiffrée, puis écrit un rapport HTML
autonome à côté de la couche.

Options utiles :

```bash
# CRS non déclaré par le fichier ? Assignez-le (n'altère pas les coordonnées) :
uv run crszone analyze couche.shp --assume-crs EPSG:4269

# Rapport HTML dans un dossier précis :
uv run crszone analyze couche.gpkg --report dossier/rapports

# Sortie JSON pure (pour un script) — le résumé humain part sur stderr :
uv run crszone analyze couche.gpkg --json > resultat.json
uv run crszone analyze couche.gpkg --json-out resultat.json   # écrit en UTF-8 garanti
```

### 2. Appliquer, reprojeter ou découper

```bash
# Interactif : l'outil propose, vous choisissez au menu
uv run crszone apply couche.gpkg --out dossier/sorties

# Non interactif : appliquer directement la recommandation
uv run crszone apply couche.gpkg --out dossier/sorties --auto

# Forcer un choix précis :
uv run crszone apply couche.gpkg --choice lambert            # Québec Lambert
uv run crszone apply couche.gpkg --choice zone --zone 8      # fuseau MTM 8
uv run crszone apply couche.gpkg --choice split              # un fichier par fuseau
```

Chaque exécution écrit la ou les couches reprojetées, plus un journal
`<nom>_journal.json` (pipeline PROJ exact appliqué, décision, avertissements).

Options : `--format gpkg|geojson|shp` · `--overwrite` (écraser une sortie existante) ·
`--assume-crs EPSG:xxxx` · `--json` / `--json-out`.

### 3. Générer la grille des fuseaux MTM, un repère visuel

```bash
uv run crszone grid --out grille_qc.geojson
```

## Lire la recommandation

L’outil recommande la projection unique la moins déformée entre le fuseau dominant et
le Québec Lambert (règle « distorsion d’abord », SPEC §4.3) :

| Motif | Sens | Que faire |
|---|---|---|
| `mono_zone` | données dans un seul fuseau | prenez ce fuseau MTM |
| `zone_dominante` | fuseau dominant, distorsion sous tolérance | prenez ce fuseau MTM (1 fichier) |
| `zone_moins_deformee` | fuseau dominant = le moins déformé, mais au-delà de la tolérance | fuseau MTM (1 fichier) **ou** découpez pour rester sous le seuil |
| `lambert_moins_deforme` | données trop étendues (province, grand nord) | prenez le Québec Lambert |

Le découpage reste toujours proposé en alternative : un fichier par fuseau, pour une
distorsion minimale. Ce choix convient si vous traitez chaque morceau séparément, moins
si vous tenez à garder un fichier unique.

## Garde-fous à connaître

- **Pas de CRS déclaré.** L’outil refuse (sortie 2) et vous invite à relancer la
  commande avec `--assume-crs EPSG:xxxx`, qui assigne une étiquette sans rien convertir.
- **Sortie déjà existante.** `apply` refuse d’écraser un résultat déjà produit, à moins
  que vous n’ajoutiez `--overwrite`.
- **Familles de datum préservées.** Une entrée NAD83 d’origine reçoit des cibles NAD83 ;
  une entrée WGS84 ou un CRS non qualifié reçoit CSRS par défaut. Le changement de datum
  silencieux n’existe pas.
- **Windows et PowerShell.** N’utilisez pas `> fichier.json` : PowerShell (le terminal
  par défaut de Windows) décode la sortie avec `[Console]::OutputEncoding` (souvent
  cp850 en français), puis la réécrit en UTF-16LE, et le fichier ressort en charabia.
  Préférez `--json-out` et `--report`, qui font écrire le fichier par l’outil lui-même ;
  le tuyau (`|`), lui, passe sans dommage.

## Codes de sortie

`0` succès · `1` erreur de données (fichier illisible, couche vide, région inconnue) ·
`2` refus explicite (CRS absent, sortie existante, non-interactif sans choix).

Pour l’aide complète : `uv run crszone --help`, `uv run crszone analyze --help`, etc.
