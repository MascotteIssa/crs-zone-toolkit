# CRS Zone Toolkit : DATA_REFERENCE (source de vérité géodésique, profil `qc`)

> **Rôle du document.** Source de vérité **unique** du moteur pour le profil Québec : codes EPSG, méridiens centraux, bornes de fuseaux, paramètres de projection. Aucune de ces valeurs ne doit être codée ailleurs que dans le profil `qc`, et aucune valeur n’entre ici sans référence ([REF-xx] → `references.md`).
>
> **Méthode de validation.** Toutes les valeurs ont été extraites le 5 juillet 2026 des exports machine du registre EPSG via epsg.io (`/{code}.json` PROJJSON et `/{code}.proj4`, pas de saisie manuelle [REF-02 à REF-09]), puis **contre-vérifiées le même jour contre le PDF officiel du MRNF** [REF-01] (édition décembre 2020, toujours la version publiée). Résultats de la contre-vérification : §7.
>
> **Version :** 0.2 · **Date :** 5 juillet 2026 · **Statut :** Vérifié epsg.io **+ contre-vérifié MRNF** ✅

---

## 1. Les familles de datum et la règle de recommandation

Trois datums coexistent dans les données québécoises (le PDF officiel [REF-01] les liste tous les trois) :

| Famille | CRS géographique | Zones MTM | Québec Lambert | Rôle pour le moteur |
|---|---|---|---|---|
| **NAD83(CSRS)** | EPSG:4617 | **26899** (fuseau 2), **2945–2952** (fuseaux 3–10) | **EPSG:6622** *(nom officiel : NAD83(CSRS)**v2** / Quebec Lambert)* | **Standard actuel** (cible recommandée par défaut) |
| NAD83 « d’origine » (1986) | EPSG:4269 | 32182–32190 (fuseaux 2–10) | EPSG:32198 | Reconnu en entrée ; cible seulement si l’entrée est dans cette famille (règle 2) |
| NAD27 (historique) | EPSG:4267 | 32082–32086 (fuseaux 2–6 seulement) | EPSG:32098 | **Entrée seulement, jamais en sortie** (voir règle 5) |

L’écart NAD83 ↔ CSRS est de l’ordre du mètre [REF-08] ; l’écart NAD27 ↔ NAD83 se compte en **dizaines de mètres** et exige la grille NTv2 (visible dans les définitions EPSG des codes NAD27 : `+nadgrids=ca_nrc_ntv2_0.tif`) [REF-09].

**Règles de recommandation du moteur (actées 2026-07-05) :**

1. Entrée en famille CSRS → recommander un code CSRS.
2. Entrée en vieux NAD83 → recommander la **même famille** (pas de changement de datum silencieux), avec note dans le rapport signalant que CSRS est le standard actuel.
3. Entrée en WGS84 ou CRS indéfini → recommander **CSRS** (défaut).
4. Le changement de famille NAD83 → CSRS n’est jamais implicite : option explicite (`--datum csrs`, V1.x) qui applique une vraie transformation et la journalise. Justification : §6.1.
5. Entrée en **NAD27** : jamais reconduit en sortie (datum obsolète). Le rapport recommande une cible CSRS en signalant explicitement qu’une **transformation de datum NTv2** sera appliquée ; l’utilisateur confirme (flux analyser → décider → agir), et le journal enregistre le pipeline PROJ utilisé.
6. **Familles exigeant une transformation exacte** (acté 2026-07-15, **DT-01**) : le profil déclare `datum.familles_grille_obligatoire` : les familles pour lesquelles une approximation (« ballpark ») est **inacceptable**. Au Québec : `["nad27"]` (écarts en dizaines de mètres). Pour toute autre paire de familles, si la grille exacte est absente, le moteur **accepte** le repli mais l’**avertit et le journalise** (§6.1). Motif : les réalisations d’une même famille moderne diffèrent de façon négligeable, notamment **EPSG:6622, qui est en NAD83(CSRS) v2** alors que 4617 et les fuseaux MTM sont en CSRS générique. Sans cette règle, l’outil **refusait le Québec Lambert qu’il venait lui-même de recommander** (chemin multi-fuseaux). Écarts mesurés (3 points au Québec, avec vs sans `ca_nrc_NA83SCRS.tif`) : **0,000 m** depuis WGS84 et depuis NAD83(CSRS) ; **0,11–0,23 m** depuis NAD83 d’origine.

---

## 2. Table maîtresse : fuseaux MTM du Québec (2 à 10)

Méridien central : **MC(n) = −58,5° − 3×(n−3)** pour n = 3…10 (fuseaux de 3°, MC ± 1,5°). Le **fuseau 2 est un cas particulier** : MC = **−56°** (voir note sous la table).

| Fuseau | Méridien central | Bande de longitudes (Québec) | EPSG **CSRS** | EPSG **NAD83 origine** | EPSG **NAD27** | Vérif. |
|---|---|---|---|---|---|---|
| 2 | **−56°** ⚠ | Est de ~57,5°O (bande essentiellement maritime, golfe du Saint-Laurent) | **26899** : NAD83(CSRS) / MTM zone 2 | 32182 : NAD83 / MTM zone 2 | 32082 | ✅ epsg.io + MRNF |
| 3 | −58,5° | 60°O → 57°O | **2945** | 32183 | 32083 | ✅ epsg.io + MRNF |
| 4 | −61,5° | 63°O → 60°O | **2946** | 32184 | 32084 | ✅ epsg.io + MRNF |
| 5 | −64,5° | 66°O → 63°O | **2947** | 32185 | 32085 | ✅ epsg.io + MRNF |
| 6 | −67,5° | 69°O → 66°O | **2948** | 32186 | 32086 | ✅ epsg.io + MRNF |
| 7 | −70,5° | 72°O → 69°O | **2949** | 32187 | — | ✅ epsg.io + MRNF |
| 8 | −73,5° | 75°O → 72°O *(+ est de l’Ontario)* | **2950** | 32188 | — | ✅ epsg.io + MRNF |
| 9 | −76,5° | 78°O → 75°O *(+ Ontario)* | **2951** | 32189 | — | ✅ epsg.io + MRNF |
| 10 | −79,5° | Ouest de 78°O (jusqu’à ~81°O) *(+ Ontario)* | **2952** | 32190 | — | ✅ epsg.io + MRNF |

> **Le cas du fuseau 2, résolu par la contre-vérification MRNF (2026-07-05).** Deux définitions coexistent dans le registre EPSG pour un « fuseau 2 » de l’est :
> - **MTM zone 2** (MC **−56°**, bande 57°30′O–54°30′O) : EPSG 26899 (CSRS) / 32182 (NAD83) / 32082 (NAD27). L’emprise déclarée au registre EPSG est « Terre-Neuve-et-Labrador », **mais c’est cette série que le PDF officiel du MRNF prescrit pour le fuseau 2 du Québec** [REF-01].
> - **SCoPQ zone 2** (MC **−55,5°**, « Québec à l’est de 57°O ») : EPSG 2944 (CSRS seulement, pas d’équivalent NAD83-origine identifié).
>
> **Décision pour le profil `qc`** : suivre la prescription de l’autorité provinciale → fuseau 2 = **26899 / 32182** (MC −56°). EPSG:2944 (SCoPQ zone 2) est **reconnu en entrée** (des utilisateurs QGIS peuvent l’avoir choisi) et traité comme équivalent du fuseau 2, avec note dans le rapport. Enjeu pratique faible : la bande du fuseau 2 ne couvre pratiquement aucune terre québécoise (l’extrémité est de la Côte-Nord s’arrête vers 57°O) : c’est un fuseau surtout maritime.

---

## 3. Paramètres de projection communs aux fuseaux MTM

Identiques pour les 9 fuseaux, dans les trois familles (seuls le méridien central et le datum varient), vérifiés sur les chaînes proj4 :

| Paramètre | Valeur |
|---|---|
| Méthode | Mercator transverse (`tmerc`) |
| Facteur d’échelle au méridien central (k₀) | **0,9999** |
| Faux Est | **304 800 m** (= 1 000 000 pieds) |
| Faux Nord | 0 m |
| Latitude d’origine | 0° |
| Ellipsoïde | GRS80 (NAD83/CSRS) · Clarke 1866 (NAD27) |

---

## 4. CRS provinciaux multi-zones

### 4.1 Québec Lambert (cible multi-zones recommandée)

| Paramètre | Valeur |
|---|---|
| Méthode | Conique conforme de Lambert, 2 parallèles (`lcc`) |
| Latitude d’origine / Méridien central | 44°N / **−68,5°** |
| Parallèles standards | **60°N et 46°N** |
| Faux Est / Faux Nord | 0 m / 0 m |

| Code | Nom officiel | Famille |
|---|---|---|
| **EPSG:6622** | NAD83(CSRS)v2 / Quebec Lambert | CSRS, **défaut du moteur** |
| EPSG:32198 | NAD83 / Quebec Lambert | NAD83 origine |
| EPSG:32098 | NAD27 / Quebec Lambert | NAD27 (entrée seulement) |

> **Libellé d’affichage** (`profil.toml` : `[profil].etiquette_multi_zones`, **optionnel**). Donnée régionale, pas une constante du noyau : le profil peut déclarer un libellé français destiné à l’interface (`qc` déclare « Québec Lambert ») ; à défaut, le moteur replie sur le nom pyproj brut du CRS résolu. Ce libellé n’habille que l’affichage : le **nom EPSG officiel reste « NAD83(CSRS)v2 / Quebec Lambert »** (table ci-dessus), qu’il ne remplace pas.

### 4.2 À reconnaître, sans les recommander (présents dans les données en circulation)

| CRS | Codes (NAD27 / NAD83 / CSRS) | Paramètres | Note |
|---|---|---|---|
| **MTQ Lambert** (ministère des Transports) | 3797 / 3798 / 3799 | `lcc`, parallèles **50°N et 46°N**, MC **−70°**, faux Est **800 000 m** | ⚠ À ne pas confondre avec le Québec Lambert : mêmes usages, paramètres différents. Beaucoup de données routières circulent dans ce CRS. |
| **Québec Albers** (équivalente) | — / 6623 / 6624 | `aea`, mêmes paramètres géométriques que le Québec Lambert | Équivalente (surfaces exactes) et non conforme. Piste V1.x : la recommander quand l’objectif est un calcul de **surfaces** (cf. feuille de route). |
| **SCoPQ zone 2** | — / — / 2944 | `tmerc`, MC **−55,5°** (Québec à l’est de 57°O) | Équivalent du **fuseau MTM 2** (le profil `qc` prescrit 26899, MC −56° ; voir §2). Reconnu en entrée (des utilisateurs QGIS ont pu le choisir), note au rapport ; jamais recommandé comme cible. |

> **Résolution de l’erratum du 2026-07-05.** Le résumé de recherche erroné (« parallèles 46°/50°, MC −70° ») décrivait en réalité le **MTQ Lambert**, pas le Québec Lambert : les deux avaient été confondus. Le PDF MRNF, qui liste les deux côte à côte, confirme les paramètres corrects de chacun.

> *Représentation profil (`profil.toml`) : chaque CRS reconnu est une entrée `[[reconnus_entree]]` (`codes`, `etiquette`). Le texte explicatif affiché vit dans `core/messages.py` (i18n). La famille de datum n’est pas stockée : elle est déduite du CRS (repli pyproj), restructuré au Jalon J2 (décision D-J2-3).*

---

## 5. CRS géographiques associés (détection d’entrée)

| Code | Nom | Rôle pour le moteur |
|---|---|---|
| EPSG:4617 | NAD83(CSRS) | Famille CSRS. Regroupe toutes les versions CSRS ≥ v2 (précision ~1 m) [REF-08]. |
| EPSG:4269 | NAD83 | Famille NAD83 d’origine. |
| EPSG:4267 | NAD27 | Datum historique (règle §1.5). |
| EPSG:4326 | WGS 84 | Entrée fréquente (GeoJSON, GPS) → règle §1.3. |

---

## 6. Notes de mise en œuvre

### 6.1 Reprojection vs transformation de datum : ce que le moteur fait réellement

Dans pyproj/PROJ, reprojection et transformation de datum passent par le même mécanisme (`Transformer`) : si la source et la cible partagent le datum, le pipeline est purement mathématique ; sinon, PROJ insère automatiquement une étape de transformation de datum **s’il en connaît une**. Le danger n’est donc pas technique mais **de politique** : sans transformation adéquate disponible, PROJ peut appliquer une transformation nulle : les coordonnées ne bougent pas, seule l’étiquette change, et l’erreur (~1 m entre NAD83 et CSRS, dizaines de mètres depuis NAD27) se cache sous une métadonnée mensongère. Preuve dans les définitions EPSG : codes vieux-NAD83 → `+towgs84=0,0,0,…` (nulle) ; codes CSRS → paramètres non nuls ; codes NAD27 → `+nadgrids=ca_nrc_ntv2_0.tif` (grille NTv2 réelle, distribuée via proj-data).

Politique du moteur : (1) les recommandations restent dans la famille d’entrée (règles §1), donc aucune transformation de datum implicite ; (2) quand une transformation est nécessaire (NAD27 → CSRS, ou `--datum csrs` en V1.x), le moteur **inspecte le pipeline choisi par PROJ** (`pyproj.transformer.TransformerGroup`), refuse ou avertit si seule une transformation approximative (« ballpark ») est disponible, et **journalise le pipeline exact**.

**Qui arbitre entre « refuse » et « avertit »** (acté 2026-07-15, DT-01, `core/apply._exige_transformation_exacte`) : la règle §1.6, c’est-à-dire le **profil**, jamais une constante du noyau (TP-40).

- Famille source **ou** cible dans `datum.familles_grille_obligatoire` (au Québec : `nad27`) → **refus** (`TransformUnavailableError`, code de sortie 1). Le message nomme la grille **réellement** manquante, extraite de l’opération indisponible la mieux classée du `TransformerGroup`, pas un nom codé en dur : la grille requise dépend de la paire de datums (`ca_nrc_NA27SCRS.tif` pour NAD27 → CSRS, `ca_nrc_NA83SCRS.tif` pour CSRS → CSRS v2), et un mauvais nom conseillerait le mauvais fichier.
- Sinon → **acceptation avertie** : la couche est reprojetée, un avertissement nomme les deux datums et la grille absente, et il remonte au **journal** via `ApplyResult.avertissements` (SPEC §9). Le pipeline journalisé porte alors la mention `Ballpark` de PROJ : la trace reste littérale.

Le mot qui porte la politique est **« silencieuse »** : ce qui est interdit, ce n’est pas l’approximation, c’est l’approximation **non dite**. L’avertissement `UserWarning` émis par pyproj lui-même est neutralisé au point d’inspection, puisque le moteur restitue la même information dans ses propres messages, en français et journalisés.

### 6.2 Génération de la grille (profil `qc`)

- Bandes de longitudes du §2, découpées sur l’emprise du Québec (les fuseaux 8–10 débordent en Ontario, 3–6 au Labrador : la grille du profil `qc` est **coupée à la frontière du Québec**).
- Attributs minimum par cellule : `zone`, `epsg_csrs`, `epsg_nad83` (nullable), `epsg_nad27` (nullable), `meridien_central`, `lon_min`, `lon_max`.
- **Emprise committée** : `regions/qc/limite_qc.geojson`, polygone du Québec dérivé des Découpages administratifs 1/100 000 [REF-15] (union des régions administratives `regio_s`, simplifiée à **0,005°** ≈ 550 m en EPSG:4326, ~168 Ko, licence CC-BY 4.0). Elle sert à la fois à **découper** la grille (défaut) et à **borner en latitude** les bandes complètes (`--no-clip`). Le noyau ne la lit pas (loi de dépendance §3) : le loader la charge (`load_boundary`) et l’injecte dans `build_grid` (décision A-07).
- La grille committée dans le dépôt (`regions/qc/grille_mtm_qc.geojson`) est générée par `crszone grid` (reproductible à l’identique, test anti-dérive TP-32).

### 6.3 Distorsion

k₀ = 0,9999 signifie ~−100 ppm au méridien central, ~0 aux lignes d’échelle vraie, croissant vers les bords de fuseau. Le rapport n’utilise **pas** cette approximation : il échantillonne la couche et calcule les facteurs exacts via `pyproj.Proj.get_factors()` [REF-13].

---

## 7. Contre-vérification MRNF : résultats (2026-07-05)

Croisement ligne à ligne avec le PDF officiel du MRNF (MERN, décembre 2020) [REF-01] :

- ✅ **Confirmé** : CRS géographiques (4267/4269/4617/4326) ; Québec Lambert 32098/32198/6622 avec parallèles **46°/60°** et MC **−68,5°** (l’erratum du §4 était la bonne correction) ; MTM fuseaux 3–10 dans les deux familles modernes.
- ✅ **Résolu** : fuseau 2 : le MRNF prescrit 32182/26899 (MC −56°), pas la SCoPQ zone 2 (2944). Décision au §2.
- ➕ **Apports du PDF** intégrés : NAD27 (§1, §5), MTQ Lambert et Québec Albers (§4.2), codes UTM fuseaux 17–21 pour le Québec (NAD83 : 26917–26921 ; CSRS : 2958–2962) → transférés à la feuille de route V2.
- ⚠ **Vigilance version** : PDF daté décembre 2020 (ministère alors nommé MERN). C’est la version encore publiée par le MRNF ; le registre EPSG reste la source canonique pour la *définition* des codes, le PDF pour *l’usage prescrit au Québec*.

Dette soldée le 2026-07-05 : la source fédérale sur le CSRS et les transformations NTv2 est [REF-14] (page officielle NRCan, outil NTv2 pour NAD27/ATS77/NAD83(Original)/NAD83(CSRS) par grilles binaires, outil TRX). Aucune dette ouverte pour ce document.

---

> *Source de vérité vivante. Toute modification passe par une vérification machine (epsg.io/PROJ) + une notice dans `references.md`. Le moteur lit ces valeurs depuis le profil `qc`, jamais en dur ailleurs.*
