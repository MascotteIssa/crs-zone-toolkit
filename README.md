# crs-zone-toolkit

[![CI](https://github.com/MascotteIssa/crs-zone-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/MascotteIssa/crs-zone-toolkit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crs-zone-toolkit.svg)](https://pypi.org/project/crs-zone-toolkit/)
[![Python](https://img.shields.io/pypi/pyversions/crs-zone-toolkit.svg)](https://pypi.org/project/crs-zone-toolkit/)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/1319874815.svg)](https://doi.org/10.5281/zenodo.21956685)

**Quel système de coordonnées pour ma couche québécoise ?** `crszone` répond avec des
chiffres. Il mesure la distorsion réellement encourue par chaque candidat (fuseau **MTM**
ou **Québec Lambert**), **recommande** la projection la moins déformante, puis
**reprojette** si vous le lui demandez. L’outil recommande ; vous décidez.

![Démonstration : analyse d’une couche des 21 régions administratives du Québec, de la ligne de commande au rapport HTML](https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/demo.gif)

## Pourquoi pas simplement `estimate_utm_crs()` ?

L’utilitaire de GeoPandas ne propose que de l’**UTM**. Il ignore les fuseaux **MTM** du
Québec, larges de 3° au lieu de 6°, alors que la distorsion croît avec le *carré* de l’écart
au méridien central : cette moitié de largeur vaut **quatre fois moins de distorsion**. Aux
latitudes habitées du Québec, un fuseau MTM tient dans −100 à +72 ppm là où l’UTM s’étale
de −400 à +287 ppm.

Sur une couche couvrant tout le Québec, il répond `EPSG:26919` (UTM 19N) : un fuseau unique
pour 23° de longitude, dont les bords tombent à plus de 11° du méridien central là où l’UTM
en prévoit 3. Rien dans sa réponse ne le signale.

Le datum subit le même sort. Une couche déclarée en NAD83 ressort en WGS 84 (`EPSG:32618`),
soit un changement de famille sans avertissement. Le paramètre `datum_name` accepte pourtant
NAD83, NAD83(CSRS) et NAD27, encore faut-il le savoir et le demander.
*(geopandas 1.1.4, pyproj 3.7.2, PROJ 9.5.1)*

Il ne mesure aucune distorsion, ne justifie rien, et ne produit ni rapport, ni découpage
multi-fuseaux, ni journal de décision.

`crszone` fait exactement cela, et rien d’autre.

## Et les outils natifs des logiciels SIG ?

ArcGIS Pro sait proposer une projection d’après l’emprise des données et la propriété à
préserver, surface, distance ou forme ([New suggested projected coordinate
system](https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/define-a-new-coordinate-system.htm)).
Il en fabrique une **sur mesure**, rangée sous « Custom », quand l’échange de données
québécoises réclame au contraire le fuseau MTM officiel ou le Québec Lambert, avec leur code
EPSG. [QGIS](https://docs.qgis.org/3.44/en/docs/user_manual/working_with_projections/working_with_projections.html)
donne accès à quelque 7 000 SCR et vous accompagne pour les assigner et les transformer, le
choix du candidat restant le vôtre.

`crszone` répond à une autre question : de combien votre couche se déforme, en ppm, dans
chacun des candidats. C’est ce chiffre qui fonde sa recommandation et qu’il inscrit au
rapport.

## Installation

```bash
pip install crs-zone-toolkit
```

```bash
uv tool install crs-zone-toolkit     # commande isolée, disponible partout
uvx crs-zone-toolkit analyze ma_couche.gpkg   # sans rien installer
```

Il vous faut Python 3.11 ou plus, et rien d’autre : la grille des fuseaux, la limite du
Québec et le profil géodésique voyagent **dans le paquet**, sans aucune donnée de référence
à télécharger.

## Sans passer par le terminal

La ligne de commande n’est pas le seul accès. La commande `crszone-gui` (installée avec
le paquet, au même titre que `crszone`) ouvre une fenêtre qui pose les mêmes questions que
le terminal. Elle appelle le même moteur, sans qu’aucune règle de décision n’y soit écrite
deux fois.

Sous Windows, l’application existe aussi en fichier unique, qui ne demande d’installer ni
Python ni quoi que ce soit d’autre. Vous le téléchargez, vous le lancez d’un double-clic :

**[Télécharger `crszone-gui.exe` pour Windows](https://github.com/MascotteIssa/crs-zone-toolkit/releases/latest/download/crszone-gui.exe)** (90 Mo)

Ce lien mène toujours à la version la plus récente. Le premier lancement demande une
dizaine de secondes, le temps que le fichier se dépaquette (environ onze secondes à froid,
cinq à six ensuite), et un écran d’attente s’affiche pendant ce temps.

Le premier des deux parcours proposés, « Traiter une couche », se déroule en quatre
étapes. Vous choisissez le fichier, l’outil l’analyse, il affiche sa recommandation avec
les chiffres qui la fondent (part de chaque fuseau, distorsion mesurée), puis vous décidez
de reprojeter, de découper par fuseau ou de ne rien faire. Le second, « Générer la grille
des fuseaux », produit le repère visuel des fuseaux MTM (le même fichier que la commande
`grid`) à ouvrir dans votre logiciel SIG.

Les sorties sont identiques à celles du terminal, rapport HTML compris, et vont dans le
dossier que vous désignez. La fenêtre suit le thème de votre système, et vous pouvez la
basculer du clair au sombre comme le rapport.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/interface-sombre.png">
  <img alt="Interface de bureau : la recommandation, ses chiffres et les décisions offertes" src="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/interface-clair.png">
</picture>

## En trente secondes

<!-- extrait:debut -->
```console
$ crszone --region qc analyze regio_s.shp
Analyse CRS : profil Québec (qc)                                                      crszone 0.2.0
───────────────────────────────────────────────────────────────────────────────────────────────────
Couche      regio_s.shp (21 entités, polygones)
CRS déclaré EPSG:4269, NAD83 (géographique)
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
    Note : NAD83(CSRS) est le standard actuel des données québécoises (écart ≈ 1 m).

  Alternative : découpage par fuseau (6 sorties, entités affectées au fuseau majoritaire).

✓ Rapport détaillé : regio_s_analyse_crs_20260728-130842.html
  Pour appliquer : crszone apply regio_s.shp
```
<!-- extrait:fin -->

Puis, quand vous êtes d’accord :

<!-- apply:debut -->
```console
$ crszone apply montreal.gpkg --out sorties --auto
Analyse CRS : profil Québec (qc)                                                      crszone 0.2.0
───────────────────────────────────────────────────────────────────────────────────────────────────
Couche      montreal.gpkg (1 entité, polygones)
CRS déclaré EPSG:4269, NAD83 (géographique)
Emprise     74,00°O → 73,47°O · 45,39°N → 45,71°N

→ Recommandation : reprojeter vers MTM fuseau 8 (EPSG:32188, NAD83 d'origine)
  Motif : Les données tiennent dans un seul fuseau (MTM 8).
  ✓ Datum : entrée NAD83 d'origine → famille préservée (EPSG:32188).
    Note : NAD83(CSRS) est le standard actuel des données québécoises (écart ≈ 1 m).

Mode --auto : application de la recommandation (MTM fuseau 8, EPSG:32188).
✓ Sortie   : sorties\montreal_epsg32188.gpkg (EPSG:32188, 1 entité)
✓ Journal  : sorties\montreal_journal.json
  Pipeline PROJ : axis order change (2D) + MTM zone 8
```
<!-- apply:fin -->

Le **pipeline PROJ exact** est affiché puis journalisé : la transformation appliquée est
vérifiable, pas devinée. Pour démarrer pas à pas, lisez
**[QUICKSTART.md](https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/QUICKSTART.md)**.

## La règle de recommandation, en deux lignes

> **Un seul fuseau traversé → ce fuseau.** Plusieurs fuseaux → la **projection unique la
> moins déformée** entre le fuseau dominant et le Québec Lambert (le fuseau l’emporte à
> égalité). Le **découpage** par fuseau est toujours offert en alternative, jamais imposé.

Cette règle n’est pas une intuition : elle a été **calibrée sur données réelles**, le
jugement d’expertise servant d’étalon. La règle précédente gatait sur la part du fuseau
dominant *avant* de regarder la distorsion, et recommandait de ce fait la projection **la
plus déformée** pour les régions compactes : le Bas-Saint-Laurent mesure 407 ppm en MTM 6
contre 5106 ppm en Québec Lambert.

## Le rapport HTML

Chaque `analyze` écrit un rapport **autonome** : un seul fichier, aucune ressource externe,
carte et styles embarqués. Il s’ouvre hors ligne, s’archive, se joint à un courriel, et
suit le thème clair ou sombre de votre système (un bouton permet de basculer).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-sombre.png">
  <img alt="Rapport HTML : verdict en tête, couche analysée, situation dans les fuseaux MTM" src="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-clair.png">
</picture>

L’élément central est l’échelle de distorsion, **divergente et centrée sur 0 ppm**, qui
rend le compromis visible d’un coup d’œil (ici, la couche des 21 régions administratives,
trop étendue pour tout fuseau MTM). La cible sort en `EPSG:32198` parce que cette donnée est
en **NAD83 d’origine** : la famille d’entrée est préservée. Sur une entrée en NAD83(CSRS),
le standard actuel, le Québec Lambert visé serait `EPSG:6622`.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-distorsion-sombre.png">
  <img alt="Échelle de distorsion divergente comparant MTM fuseau 8 et Québec Lambert" src="https://raw.githubusercontent.com/MascotteIssa/crs-zone-toolkit/main/docs/images/rapport-distorsion-clair.png">
</picture>

## Pour un script

`--json` écrit le résultat sur la sortie standard, le résumé humain sur l’erreur standard :

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
suite de tests. L’API Python (`analyze`, `apply`, `report`) est typée et livre son marqueur
[PEP 561](https://peps.python.org/pep-0561/).

Codes de sortie : `0` succès · `1` erreur de données · `2` refus explicite (CRS absent,
sortie existante, non interactif sans choix).

> **Windows / PowerShell : préférez `--json-out` à `>`.** La redirection `>` de PowerShell
> ne transmet pas les octets du programme : elle les **décode** d’abord avec
> `[Console]::OutputEncoding`, puis les **réécrit** dans son propre encodage. Sur une console
> française laissée en cp850/cp1252, l’UTF-8 émis par `crszone` est mal décodé (`donn├®es`),
> et PowerShell 5.1 écrit ensuite le fichier en **UTF-16LE**, pas en UTF-8. Le résultat est
> illisible pour la plupart des outils.
>
> **L’outil n’y est pour rien** : il émet bien de l’UTF-8 sur ses flux (DT-15), et le tuyau
> (`|`) passe sans dommage. Le remède tient en un mot : laissez `crszone` écrire le fichier
> lui-même, avec **`--json-out`** pour le JSON et **`--report`** pour le rapport HTML.
>
> Si vous tenez à rediriger, corrigez d’abord le décodage avec
> `[Console]::OutputEncoding = [Text.Encoding]::UTF8`, puis écrivez avec
> `| Out-File -Encoding utf8`. *(Vérifié dans les deux sens : console en cp850 → fichier
> corrompu ; console en UTF-8 → fichier valide.)*


## Ce que l’outil ne fait pas

Il ne change **jamais** de famille de datum en silence : une transformation approximative
est soit refusée, soit exécutée avec un avertissement journalisé (NAD27 exige la grille
NTv2). Il ne recommande rien pour les données tombant hors du Québec, il le signale. Il
n’écrase aucun fichier sans `--overwrite`. Il ne produit ni PDF, ni sortie texte, et
n’accède **à aucun réseau**, ni à l’exécution ni dans ses tests.

Il n’est pas conçu pour les très gros volumes : le traitement est **en mémoire** et l’outil
vise des couches de l’ordre de 10⁴ à 10⁵ entités (12 580 lignes s’analysent en 6,1 s).
L’échantillonnage de distorsion est plafonné, mais la répartition par fuseau et le
découpage croissent avec le nombre d’entités : au-delà, prévoyez de découper la couche en
amont.

Le périmètre V1 est le Québec. Le noyau ne connaît aucun code EPSG : tous les faits
géodésiques viennent d’un **profil de région** (`regions/qc/`), ce que verrouille un test
dédié. C’est ce qui rendra possible l’extension au reste du Canada, puis ailleurs.

## Documentation

| Document | Rôle |
|---|---|
| [`QUICKSTART.md`](https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/QUICKSTART.md) | Les trois commandes, options utiles, garde-fous |
| [`docs/DATA_REFERENCE.md`](https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/docs/DATA_REFERENCE.md) | Source de vérité géodésique (codes EPSG vérifiés) |
| [`docs/references.md`](https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/docs/references.md) | Bibliographie (APA 7), toute décision est sourcée |

Les sigles `DT-xx` et `N-xx` cités au fil de ces pages sont les identifiants du registre de
dette technique et des observations du test manuel, tenus au dépôt de développement et non
publiés.

## Attributions

- **Codes EPSG** : registre EPSG (IOGP) via epsg.org / epsg.io ; usage québécois d’après
  MERN/MRNF, *Codes EPSG des projections utilisées au Québec*, décembre 2020.
- **Grille des fuseaux et limite du Québec** : découpées d’après MRNF, *Découpages
  administratifs*, Données Québec, licence **CC-BY 4.0**. Les captures et le rapport
  d’exemple de ce README sont dérivés du même jeu.

## English summary

`crs-zone-toolkit` helps you choose a metric projection before spatial analysis in
Québec, Canada: it reports which MTM zones your data spans, measures the actual
distortion of each candidate CRS with `pyproj`, recommends the least-distorted single
projection, and reprojects or splits your layer with a full decision log. Unlike a
plain UTM guess, every recommendation comes with measured evidence and a self-contained
HTML report. **The command line, reports and documentation are in French.**

## Licence

MIT, voir [`LICENSE`](https://github.com/MascotteIssa/crs-zone-toolkit/blob/main/LICENSE). © 2026 Issa Moussahoudou.
