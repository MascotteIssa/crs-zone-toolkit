# crszone — démarrage rapide

`crszone` analyse une couche vectorielle, **recommande** un système de coordonnées
adapté au Québec (fuseau MTM ou Québec Lambert), et **reprojette** sur demande.
L'outil recommande ; **vous décidez** (rien n'est reprojeté sans votre accord).

> Exemples préfixés `uv run` (environnement de développement). Après installation du
> paquet, la commande s'appelle directement `crszone`.

## Les 3 commandes

### 1. Analyser (lecture seule) — que faire de ma couche ?

```bash
uv run crszone analyze chemin/vers/couche.gpkg
```

Affiche : CRS déclaré, emprise, répartition par fuseau MTM, distorsion des candidats,
et une **recommandation chiffrée**. Écrit aussi un rapport HTML autonome à côté de la couche.

Options utiles :

```bash
# CRS non déclaré par le fichier ? Assignez-le (n'altère pas les coordonnées) :
uv run crszone analyze couche.shp --assume-crs EPSG:4269

# Rapport HTML dans un dossier précis :
uv run crszone analyze couche.gpkg --report dossier/rapports

# Sortie JSON pure (pour un script) — le résumé humain part sur stderr :
uv run crszone analyze couche.gpkg --json > resultat.json
uv run crszone analyze couche.gpkg --json-out resultat.json   # écrit en UTF-8 garanti
```

### 2. Appliquer — reprojeter ou découper

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

Chaque exécution écrit la ou les couches reprojetées **plus** un journal
`<nom>_journal.json` (pipeline PROJ exact appliqué, décision, avertissements).

Options : `--format gpkg|geojson|shp` · `--overwrite` (écraser une sortie existante) ·
`--assume-crs EPSG:xxxx` · `--json` / `--json-out`.

### 3. Générer la grille des fuseaux MTM (repère visuel)

```bash
uv run crszone grid --out grille_qc.geojson
```

## Lire la recommandation

L'outil recommande **la projection unique la moins déformée** entre le fuseau dominant
et le Québec Lambert (règle « distorsion d'abord », SPEC §4.3) :

| Motif | Sens | Que faire |
|---|---|---|
| `mono_zone` | données dans un seul fuseau | prenez ce fuseau MTM |
| `zone_dominante` | fuseau dominant, distorsion sous tolérance | prenez ce fuseau MTM (1 fichier) |
| `zone_moins_deformee` | fuseau dominant = le moins déformé, mais au-delà de la tolérance | fuseau MTM (1 fichier) **ou** découpez pour rester sous le seuil |
| `lambert_moins_deforme` | données trop étendues (province, grand nord) | prenez le Québec Lambert |

Le **découpage** est toujours proposé en alternative (un fichier par fuseau, distorsion
minimale) — utile si vous traiterez chaque morceau séparément, moins pratique pour garder
un fichier unique.

## Garde-fous à connaître

- **Pas de CRS déclaré** → l'outil refuse (sortie 2) et explique : relancez avec
  `--assume-crs EPSG:xxxx` (assigne une étiquette, ne convertit rien).
- **Sortie déjà existante** → `apply` refuse d'écraser sans `--overwrite`.
- **Familles de datum préservées** : entrée NAD83 d'origine → cibles NAD83 ; entrée
  WGS84 ou CRS non qualifié → CSRS par défaut ; jamais de changement de datum silencieux.
- **Windows / PowerShell** : n'utilisez pas `> fichier.json`. PowerShell décode la sortie
  avec `[Console]::OutputEncoding` (souvent cp850 en français) puis la réécrit en UTF-16LE :
  le fichier ressort en charabia. Utilisez **`--json-out`** et **`--report`**, qui font écrire
  le fichier par l'outil lui-même. Le tuyau (`|`), lui, passe sans dommage.


## Codes de sortie

`0` succès · `1` erreur de données (fichier illisible, couche vide, région inconnue) ·
`2` refus explicite (CRS absent, sortie existante, non-interactif sans choix).

Aide complète : `uv run crszone --help`, `uv run crszone analyze --help`, etc.
