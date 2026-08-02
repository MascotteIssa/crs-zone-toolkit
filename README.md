# crs-zone-toolkit

[![CI](https://github.com/MascotteIssa/crs-zone-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/MascotteIssa/crs-zone-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crs-zone-toolkit.svg)](https://pypi.org/project/crs-zone-toolkit/)
[![Python](https://img.shields.io/pypi/pyversions/crs-zone-toolkit.svg)](https://pypi.org/project/crs-zone-toolkit/)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

**Quel système de coordonnées pour ma couche québécoise ?** `crszone` répond avec des
chiffres : il mesure la distorsion réellement encourue par chaque candidat, **recommande**
la projection la moins déformante — fuseau **MTM** ou **Québec Lambert** — et **reprojette**
si vous le lui demandez. L'outil recommande ; vous décidez.

![Démonstration : analyse d'une couche des 21 régions administratives du Québec, de la ligne de commande au rapport HTML](https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/demo.gif)

## Pourquoi pas simplement `estimate_utm_crs()` ?

L'utilitaire de GeoPandas ne connaît que l'**UTM**. Il ignore les fuseaux **MTM** du Québec,
larges de 3° au lieu de 6° — et comme la distorsion croît avec le *carré* de l'écart au
méridien central, cette moitié de largeur vaut **quatre fois moins de distorsion** : aux
latitudes habitées du Québec, un fuseau MTM tient dans −100 à +72 ppm là où l'UTM s'étale
de −400 à +287 ppm. Il ignore aussi le **Québec Lambert**, et les familles de datum
canadiennes — NAD83 d'origine, NAD83(CSRS), NAD27 — qu'il ne faut jamais franchir en
silence. Il ne mesure aucune distorsion, ne justifie rien, et ne produit ni rapport, ni
découpage multi-fuseaux, ni journal de décision.

`crszone` fait exactement cela, et rien d'autre.

## Installation

```bash
pip install crs-zone-toolkit
```

```bash
uv tool install crs-zone-toolkit     # commande isolée, disponible partout
uvx crs-zone-toolkit analyze ma_couche.gpkg   # sans rien installer
```

Python 3.11 ou plus. Aucune donnée de référence à télécharger : la grille des fuseaux, la
limite du Québec et le profil géodésique voyagent **dans le paquet**.

## En trente secondes

<!-- extrait:debut -->
```console
$ crszone analyze regio_s.shp --region qc
Analyse CRS — profil Québec (qc)                                                      crszone 0.1.0
───────────────────────────────────────────────────────────────────────────────────────────────────
Couche      regio_s.shp (21 entités, polygones)
CRS déclaré EPSG:4269 — NAD83 (géographique)
Emprise     79,77°O → 56,93°O · 44,99°N → 62,58°N

Répartition par fuseau MTM (part de la surface totale)
  Fuseau  8 (MC −73,5°)  ████                   22,2 %
  Fuseau  9 (MC −76,5°)  ████                   19,9 %
  Fuseau  7 (MC −70,5°)  ████                   19,3 %
  Fuseau  6 (MC −67,5°)  ███                    12,8 %
  Fuseau  5 (MC −64,5°)  ██                     10,0 %
  Fuseau  4 (MC −61,5°)  █                       7,4 %
  Fuseau 10 (MC −79,5°)  █                       5,4 %
  Fuseau  3 (MC −58,5°)  █                       3,0 %
  Fuseau  2 (MC −56,0°)                          0,0 %

Distorsion mesurée (187 points d'échantillonnage)
  Candidat                               min         moy         max
  MTM fuseau 8 (tout) EPSG:32188    −100 ppm   +1564 ppm  +14784 ppm  ⚠ hors seuil
  Québec Lambert      EPSG:32198   −7458 ppm   −2814 ppm   +2149 ppm  ⚠ hors seuil

→ Recommandation : reprojeter vers Québec Lambert (EPSG:32198, NAD83 d'origine)
  Motif : Les données sont trop étendues pour le fuseau dominant (MTM 8 : 14784 ppm) : le Québec
  Lambert est la projection unique la moins déformée (7458 ppm max). Découpage disponible en
  alternative.
  ✓ Datum : entrée NAD83 d'origine → famille préservée (EPSG:32198).
    Note : NAD83(CSRS) est le standard actuel des données québécoises — écart ≈ 1 m.

  Alternative : découpage par fuseau (6 sorties, entités affectées au fuseau majoritaire).

✓ Rapport détaillé : regio_s_analyse_crs_20260728-130842.html
  Pour appliquer : crszone apply regio_s.shp
```
<!-- extrait:fin -->

Puis, quand vous êtes d'accord :

<!-- apply:debut -->
```console
$ crszone apply montreal.gpkg --out sorties --auto
Analyse CRS — profil Québec (qc)                                                      crszone 0.1.0
───────────────────────────────────────────────────────────────────────────────────────────────────
Couche      montreal.gpkg (1 entité, polygones)
CRS déclaré EPSG:4269 — NAD83 (géographique)
Emprise     74,00°O → 73,47°O · 45,39°N → 45,71°N

→ Recommandation : reprojeter vers MTM fuseau 8 (EPSG:32188, NAD83 d'origine)
  Motif : Les données tiennent dans un seul fuseau (MTM 8).
  ✓ Datum : entrée NAD83 d'origine → famille préservée (EPSG:32188).
    Note : NAD83(CSRS) est le standard actuel des données québécoises — écart ≈ 1 m.

Mode --auto : application de la recommandation (MTM fuseau 8, EPSG:32188).
✓ Sortie   : sorties\montreal_epsg32188.gpkg (EPSG:32188, 1 entité)
✓ Journal  : sorties\montreal_journal.json
  Pipeline PROJ : axis order change (2D) + MTM zone 8
```
<!-- apply:fin -->

Le **pipeline PROJ exact** est affiché puis journalisé : la transformation appliquée est
vérifiable, pas devinée. Démarrage complet : **[QUICKSTART.md](QUICKSTART.md)**.

## La règle de recommandation, en deux lignes

> **Un seul fuseau traversé → ce fuseau.** Plusieurs fuseaux → la **projection unique la
> moins déformée** entre le fuseau dominant et le Québec Lambert (le fuseau l'emporte à
> égalité). Le **découpage** par fuseau est toujours offert en alternative, jamais imposé.

Cette règle n'est pas une intuition : elle a été **calibrée sur données réelles**, le
jugement d'expertise servant d'étalon. La règle précédente gatait sur la part du fuseau
dominant *avant* de regarder la distorsion, et recommandait de ce fait la projection **la
plus déformée** pour les régions compactes — le Bas-Saint-Laurent mesure 407 ppm en MTM 6
contre 5106 ppm en Québec Lambert. Méthodologie, balayage et décision :
[`docs/calibrage/`](docs/calibrage/2026-07-19-calibrage-seuils.md) · formalisation :
[SPEC §4.3](docs/SPEC.md).

## Le rapport HTML

Chaque `analyze` écrit un rapport **autonome** : un seul fichier, aucune ressource externe,
carte et styles embarqués. Il s'ouvre hors ligne, s'archive, se joint à un courriel — et
suit le thème clair ou sombre de votre système, avec un bouton pour basculer.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-sombre.png">
  <img alt="Rapport HTML : verdict en tête, couche analysée, situation dans les fuseaux MTM" src="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-clair.png">
</picture>

L'élément central est l'échelle de distorsion, **divergente et centrée sur 0 ppm**, qui
rend le compromis visible d'un coup d'œil — ici, la couche des 21 régions administratives,
trop étendue pour tout fuseau MTM. La cible sort en `EPSG:32198` parce que cette donnée est
en **NAD83 d'origine** : la famille d'entrée est préservée. Sur une entrée en NAD83(CSRS),
le standard actuel, le Québec Lambert visé serait `EPSG:6622`.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-distorsion-sombre.png">
  <img alt="Échelle de distorsion divergente comparant MTM fuseau 8 et Québec Lambert" src="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-distorsion-clair.png">
</picture>

**[Ouvrir un rapport réel](docs/exemple_rapport.html)** *(clic droit → enregistrer, puis
ouvrir dans un navigateur — GitHub n'exécute pas le HTML des dépôts).*

## Pour un script

`--json` écrit le résultat sur la sortie standard, le résumé humain sur l'erreur standard :

```console
$ crszone analyze montreal.gpkg --json | jq .recommandation
{
  "action": "zone",
  "cible_epsg": 32188,
  "cible_libelle": "MTM fuseau 8",
  "motif_code": "mono_zone",
  "motif": "Les données tiennent dans un seul fuseau (MTM 8).",
  "alternatives": []
}
```

Le contrat est **versionné** (`schema_version`) et validé par un schéma JSON Schema dans la
suite de tests. L'API Python (`analyze`, `apply`, `report`) est typée et livre son marqueur
[PEP 561](https://peps.python.org/pep-0561/).

Codes de sortie : `0` succès · `1` erreur de données · `2` refus explicite (CRS absent,
sortie existante, non interactif sans choix).

> **Windows / PowerShell — préférez `--json-out` à `>`.** La redirection `>` de PowerShell
> ne transmet pas les octets du programme : elle les **décode** d'abord avec
> `[Console]::OutputEncoding`, puis les **réécrit** dans son propre encodage. Sur une console
> française laissée en cp850/cp1252, l'UTF-8 émis par `crszone` est mal décodé (`donn├®es`) —
> et PowerShell 5.1 écrit ensuite le fichier en **UTF-16LE**, pas en UTF-8. Le résultat est
> illisible pour la plupart des outils.
>
> **L'outil n'y est pour rien** : il émet bien de l'UTF-8 sur ses flux (DT-15), et le tuyau
> (`|`) passe sans dommage. Le remède tient en un mot : laissez `crszone` écrire le fichier
> lui-même, avec **`--json-out`** pour le JSON et **`--report`** pour le rapport HTML.
>
> Si vous tenez à rediriger, corrigez d'abord le décodage —
> `[Console]::OutputEncoding = [Text.Encoding]::UTF8` — puis écrivez avec
> `| Out-File -Encoding utf8`. *(Vérifié dans les deux sens : console en cp850 → fichier
> corrompu ; console en UTF-8 → fichier valide.)*


## Ce que l'outil ne fait pas

Il ne change **jamais** de famille de datum en silence : une transformation approximative
est soit refusée, soit exécutée avec un avertissement journalisé (NAD27 exige la grille
NTv2). Il ne recommande rien pour les données tombant hors du Québec — il le signale. Il
n'écrase aucun fichier sans `--overwrite`. Il ne produit ni PDF, ni sortie texte, et
n'accède **à aucun réseau**, ni à l'exécution ni dans ses tests.

Il n'est pas conçu pour les très gros volumes : le traitement est **en mémoire** et l'outil
vise des couches de l'ordre de 10⁴ à 10⁵ entités (12 580 lignes s'analysent en 6,1 s).
L'échantillonnage de distorsion est plafonné, mais la répartition par fuseau et le
découpage croissent avec le nombre d'entités : au-delà, prévoyez de découper la couche en
amont.

Le périmètre V1 est le Québec. Le noyau ne connaît aucun code EPSG : tous les faits
géodésiques viennent d'un **profil de région** (`regions/qc/`), ce que verrouille un test
dédié. C'est ce qui rendra possible l'extension au reste du Canada, puis ailleurs
([feuille de route](docs/feuille_de_route.md)).

## Documentation

| Document | Rôle |
|---|---|
| [`QUICKSTART.md`](QUICKSTART.md) | Les trois commandes, options utiles, garde-fous |
| [`docs/SPEC.md`](docs/SPEC.md) | Cahier des charges fonctionnel V1 |
| [`docs/DATA_REFERENCE.md`](docs/DATA_REFERENCE.md) | Source de vérité géodésique (codes EPSG vérifiés) |
| [`docs/calibrage/`](docs/calibrage/2026-07-19-calibrage-seuils.md) | Calibrage de la règle de décision sur données réelles |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Noyau + adaptateurs, lois de dépendance, API |
| [`docs/CLI_UX.md`](docs/CLI_UX.md) | Maquette du flux terminal |
| [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) | Jeux de test et protocole de calibrage |
| [`docs/feuille_de_route.md`](docs/feuille_de_route.md) | Évolutions (Québec → Canada → international) |
| [`docs/references.md`](docs/references.md) | Bibliographie (APA 7) — toute décision est sourcée |

## Attributions

- **Codes EPSG** : registre EPSG (IOGP) via epsg.org / epsg.io ; usage québécois d'après
  MERN/MRNF, *Codes EPSG des projections utilisées au Québec*, décembre 2020.
- **Grille des fuseaux et limite du Québec** : découpées d'après MRNF, *Découpages
  administratifs*, Données Québec, licence **CC-BY 4.0**. Les captures et le rapport
  d'exemple de ce README sont dérivés du même jeu.

## English summary

`crs-zone-toolkit` helps you choose a metric projection before spatial analysis in
Québec, Canada: it reports which MTM zones your data spans, measures the actual
distortion of each candidate CRS with `pyproj`, recommends the least-distorted single
projection, and reprojects or splits your layer with a full decision log. Unlike a
plain UTM guess, every recommendation comes with measured evidence and a self-contained
HTML report. **The command line, reports and documentation are in French.**

## Licence

MIT — voir [`LICENSE`](LICENSE). © 2026 Issa Moussahoudou.
