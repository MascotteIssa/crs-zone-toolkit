# Calibrage de la règle de décision — MTM unique vs Québec Lambert

> **Rôle du document.** Registre **vivant** du calibrage des seuils de recommandation
> (`crs_zone_toolkit`), TEST_PLAN §5. Il documente, au fil de l'eau, la méthodologie,
> les résultats chiffrés et les décisions — pensé pour servir de matière à une
> publication ultérieure (revue de géomatique).
>
> **Créé le :** 2026-07-19 · **Données :** Système sur le découpage administratif (SDA)
> du Québec, `regio_s` (21 régions administratives, NAD83 EPSG:4269). Les données brutes
> ne sont **pas** versionnées (TEST_PLAN §6).

---

## 1. Question de calibrage

L'outil recommande, pour une couche traversant plusieurs fuseaux MTM, soit **un fuseau
MTM unique** (faible distorsion locale, un seul fichier), soit le **Québec Lambert**
(conique conforme provincial). Deux paramètres nommés au profil encadraient ce choix :

| Paramètre | Défaut (hypothèse) | Rôle initial |
|---|---|---|
| `part_dominante_min` | 0,90 | part minimale du fuseau dominant pour recommander ce fuseau |
| `distorsion_max_ppm` | 200 | distorsion maximale tolérée (ppm, max en valeur absolue) |

Ces valeurs étaient des **hypothèses jamais mesurées**. Objectif du §5 : les confronter à
des cas réels, avec le **jugement d'un expert humain comme étalon** (TEST_PLAN §5 : « c'est
le juge, pas l'outil »).

## 2. Méthodologie

### 2.1 Construction de cas limites réels

Plutôt que des géométries synthétiques, on extrait des **sous-ensembles de la SDA** dont
le fuseau dominant balaie la zone critique du seuil (≈ 85–95 %). Chaque sous-ensemble est
analysé par le **moteur réel** de l'outil (`crs_zone_toolkit.analyze`), garantissant que
les chiffres de calibrage sont ceux que produira l'outil livré.

Deux régions administratives tombent naturellement près du seuil, sans manipulation :
**Mauricie** (86,5 % dans le fuseau 8) et **Capitale-Nationale** (87,2 % dans le fuseau 7).
Des combinaisons de régions produisent des points au-dessus de 90 %.

### 2.2 Métrique de distorsion

Pour chaque CRS candidat, facteurs d'échelle linéaires exacts via `pyproj.Proj.get_factors()`
sur l'échantillon de la couche (contour des polygones, ~200 points, déterministe — SPEC §4.2.4).
On retient `max(|min_ppm|, |max_ppm|)` comme distorsion représentative du candidat.
Point important : la distorsion du **fuseau dominant** est mesurée sur **tout** l'échantillon
(y compris les portions hors du fuseau) — donc une couche étalée fait naturellement grimper
cette valeur.

### 2.3 Balayage

Pour chaque cas, on compare la distorsion du **fuseau dominant** à celle du **Québec Lambert**,
et on confronte la recommandation de l'outil au jugement de l'expert.

## 3. Résultats

### 3.1 Autour du seuil de 90 % (régions compactes du sud)

| Cas (sous-ensemble réel) | Dominant | MTM dom. (max ppm) | Lambert (max ppm) |
|---|---|---|---|
| Mauricie | f.8 = 86,5 % | **181** | 4883 |
| Capitale-Nationale | f.7 = 87,2 % | **194** | 3802 |
| Mauricie + Lanaudière | f.8 = 89,9 % | **180** | 4883 |
| Mauricie + Lanaudière + Montérégie | f.8 = 91,5 % | **182** | 4883 |
| Cap-Nat + Chaudière-Appalaches | f.7 = 92,7 % | **192** | 3802 |

**Constat 1.** Sur toute la plage 86–93 %, le fuseau dominant reste à **180–194 ppm**
(à/​sous la tolérance de 200), tandis que le Lambert reste à **3800–4900 ppm** — soit
20 à 27× plus. L'ancienne règle (portillon `part ≥ 0,90` *avant* la distorsion) envoyait
au Lambert les cas < 90 % (Mauricie, Capitale-Nationale, Mauricie+Lanaudière) : elle
recommandait donc la projection **la plus déformée**.

### 3.2 Balayage géographique large (nord dispersé, allongées est-ouest)

| Cas | Dominant | MTM dom. | Lambert | Le moins déformé |
|---|---|---|---|---|
| Bas-Saint-Laurent | f.6 = 75,2 % | **407** | 5106 | fuseau (12×) |
| Gaspésie | f.5 = 43,9 % | **1020** ¹ | 5681 | fuseau |
| Côte-Nord extrême-est | f.4 = 46,0 % | **1105** | 7449 | fuseau |
| Nord-du-Québec | f.9 = 29,7 % | 8202 ¹ | **7456** | Lambert |
| `regio_s` complet (province) | f.8 = 22,2 % | 14784 | **7458** | Lambert |

> ¹ **Valeurs révisées le 2026-08-01 (DT-24), après re-mesure sur les mêmes données.**
> Publiées à l'origine à **1058** et **8203** ; la part hors profil est désormais exclue de
> l'assiette de mesure de la distorsion. **Les neuf cas ont été rejoués : sept sont identiques
> au chiffre près, et les neuf recommandations sont inchangées** — aucun `motif_code` ne bouge,
> donc aucune conclusion de ce calibrage n'est affectée.
>
> **Ce qui a bougé, et pourquoi c'est un argument pour le correctif.** Seules ces deux régions
> ont une part hors profil non nulle — **0,033 %** (Gaspésie) et **0,027 %** (Nord-du-Québec),
> des échardes de la limite simplifiée (0,005°), sous le seuil d'affichage de DT-12 donc jamais
> signalées. Cette écharde de 0,03 % déplaçait la distorsion mesurée de la Gaspésie de **38 ppm,
> soit 3,6 %** : quelques points de contour tombant marginalement hors de la limite étaient les
> plus éloignés de la méridienne centrale du fuseau 5, donc les plus déformés.
>
> **Le second correctif de DT-24 — la décimation qui ne retenait jamais le dernier indice — ne
> déplace, lui, aucun chiffre de ce calibrage.** Vérifié en isolant les deux correctifs l'un de
> l'autre : décimation seule = valeurs d'origine sur les neuf cas.
>
> Le §2.2 ci-dessus (« la distorsion du fuseau dominant est mesurée sur **tout** l'échantillon,
> y compris les portions hors du fuseau ») reste exact : l'exclusion porte sur le hors-**profil**,
> pas sur le hors-**fuseau**. Une couche étalée fait toujours grimper la valeur du fuseau dominant.

**Constat 2.** Le Québec Lambert n'est la projection unique la moins déformée que pour
les données **province-entière ou grand-nord**. Pour la plupart des régions multi-fuseaux
(y compris allongées est-ouest), le **fuseau dominant est moins déformé**. Raison physique :
aux latitudes du Québec (50–53°N), le Québec Lambert (parallèles standards 46°/60°) subit
une contraction de −5000 à −7500 ppm ; un fuseau MTM (3° de large) reste sous ~1000–2000 ppm
tant que la couche n'excède pas quelques degrés de longitude.

## 4. Décision (2026-07-19)

**Règle « distorsion d'abord » (B2), variante « titre = single le moins déformé » (a) :**

1. Un seul fuseau → ce fuseau.
2. Plusieurs fuseaux → recommander la **projection unique la moins déformée** entre le
   fuseau dominant et le Québec Lambert (le fuseau l'emporte à égalité : un fichier local
   vaut mieux que le Lambert provincial).
   - fuseau gagnant, distorsion ≤ `distorsion_max_ppm` → motif `zone_dominante` ;
   - fuseau gagnant, distorsion > `distorsion_max_ppm` → motif `zone_moins_deformee`
     (le découpage par fuseau est mis en avant pour ramener chaque morceau sous le seuil) ;
   - Lambert gagnant → motif `lambert_moins_deforme`.
3. Le **découpage** reste offert en alternative (jamais imposé) : il fragmente le
   traitement (N fichiers, N contextes de mesure en SIG), donc il n'est pas le titre par
   défaut — l'utilisateur qui veut un fichier unique utilisable l'obtient toujours.

**Validation end-to-end** (moteur réel, après implémentation) :

| Couche | Recommandation | Motif |
|---|---|---|
| Montréal (mono) | MTM 8 (32188) | `mono_zone` |
| Mauricie (87 %) | MTM 8 (32188) | `zone_dominante` |
| Bas-Saint-Laurent | MTM 6 (32186) | `zone_moins_deformee` (sans découpage ¹) |
| `regio_s` (province) | Québec Lambert (32198) | `lambert_moins_deforme` |
| Nord-du-Québec | Québec Lambert (32198) | `lambert_moins_deforme` |

> ¹ **Révisé le 2026-08-02 (observations N20/N23).** Le Bas-Saint-Laurent traverse trois
> fuseaux [6, 7, 5] mais n'en a qu'**un** de majoritaire : le découpage y produirait **un seul**
> fichier, à 407 ppm — inchangé. L'alternative n'est donc plus proposée, et le motif ne promet
> plus qu'elle « garde chaque morceau sous le seuil ». La recommandation elle-même — MTM 6 — et
> tous les chiffres de ce calibrage sont **inchangés** : seul l'accompagnement du verdict l'est.
> Voir SPEC §4.3 point 3, amendé.

## 5. Conséquences sur les paramètres

- **`distorsion_max_ppm` (200)** devient le **seul seuil actif**. Il ne gate plus le choix
  MTM/Lambert (fait par comparaison directe) mais **qualifie** le résultat : sépare
  « fuseau sous tolérance » du cas « fuseau le moins déformé mais au-delà → découpage ».
  Marge confortable observée : les cas compacts plafonnent à 194 ppm, les cas allongés
  démarrent à 407 ppm — aucun cas réel ne s'assoit près de 200 (bordure non stressée).
- **`part_dominante_min` (0,90)** n'est **plus consulté**. Conservé au profil et au JSON
  pour transparence (**DT-16** : retrait propre au prochain changement de schéma).

## 6. Reproductibilité

Les balayages sont produits par un court script Python qui, pour chaque sous-ensemble de
`regio_s` (indices de features), appelle `crs_zone_toolkit.analyze` et lit
`result.zones_traversees` + `result.distorsions`. Le script n'a pas de dépendance hors
`geopandas` + le paquet ; il opère sur la SDA (non versionnée — TEST_PLAN §6).

## 7. Limites & suites

- **Bordure du seuil de distorsion non stressée** : aucun cas réel n'a une distorsion de
  fuseau dominant proche de 200 ppm — les compacts plafonnent à 194, les allongés démarrent
  à 407. La valeur 200 n'est donc **pas pincée** par les données actuelles ; un cas construit
  à ~200 ppm affinerait.

  **Amendement du 2026-08-01 (test manuel v2.0, §10 question 1) — le seuil n'est pas
  arbitraire pour autant.** 200 ppm vaut le **double du budget de conception du MTM
  québécois**. Le MTM utilise k₀ = 0,9999, soit **−100 ppm** à la méridienne centrale ;
  au bord d'un fuseau (1,5° du MC, ≈ 116 km vers 46° N), la correction de Mercator
  transverse remonte à ≈ +166 ppm, soit **+66 ppm** net. Une couche **entièrement contenue
  dans son fuseau** vit donc dans **[−100, +66] ppm — jamais au-delà de 100 en valeur
  absolue**. Le seuil est un multiple d'une constante géodésique publique, pas une
  intuition. **Conséquence pratique : ne pas déplacer 200** — l'intervalle 194-407 étant
  vide, tout déplacement serait infalsifiable sur les données actuelles.

  *Corollaire relevé, sans action : entre 100 et 200 ppm, une couche déborde déjà de son
  fuseau et ne reçoit aucun marqueur (c'est le cas de la Mauricie à 181 ppm). Si un second
  seuil devait exister un jour, **100 ppm** en est le candidat naturel, étant le budget de
  conception lui-même. Sujet V2 : le poser exigerait un recalibrage complet.*
- **Biais SDA** (source de notre propre limite du Québec) : `part_hors_profil ≈ 0` par
  construction — le calibrage n'exerce pas le chemin « hors profil ».

  **Note du 2026-08-01 :** ce biais est ce qui rend **DT-24** peu risquée. Exclure la part
  hors profil de l'assiette de mesure de la distorsion ne déplacerait **aucun** chiffre de
  ce calibrage, précisément parce que cette part y est nulle par construction.
- **La distorsion mesurée dépend du découpage en entités** (limite assumée, ajoutée le
  2026-08-01 — observation N10 du test manuel v2.0) : le budget
  d'échantillonnage étant `max(2, 200 // n_entités)` **par entité**, un même territoire
  donne **181 ppm** en 1 polygone et **99 ppm** en 57 municipalités, à emprise identique.
  **Les seuils de ce calibrage ont été réglés sur l'échantillonnage actuel** : y toucher
  invaliderait les valeurs ci-dessus et exigerait de tout reprendre. Sujet V2.
- **Suite possible** : élargir aux couches hydrographiques (GRHQ) pour d'autres géographies,
  et statuer sur le retrait de `part_dominante_min` (DT-16).
