# CRS Zone Toolkit — Feuille de route & registre d'évolutions

> **Rôle du document.** Référencer toutes les améliorations, ajouts et extensions envisagés, pour garder un œil dessus pendant le développement et faire en sorte que la scalabilité se fasse **sans friction** : chaque décision de la V1 est prise en connaissance de ce qui viendra après. Registre vivant — toute nouvelle idée s'ajoute ici plutôt que de se perdre dans une conversation.
>
> **Version :** 0.2 · **Date :** 28 juillet 2026 · **Statut :** Référence vivante
>
> **Historique.** v0.2 (28 juillet 2026) — amendements A1-A7 issus de l'annexe A de la vision V2 du 2026-07-16, arbitrés « oui, tous » par l'utilisateur le 2026-07-28 ; complétés d'un huitième point (validation de complétude des familles au chargeur, revue Phase A).

---

## 1. Principes de scalabilité — à respecter dès la V1

Ces contraintes ne coûtent presque rien maintenant et évitent une réécriture plus tard. Elles sont **non négociables** pendant la conception :

1. **Moteur région-agnostique.** Le moteur (détection zones × emprise, distorsion, règles de seuil, reprojection/découpage, génération de rapport) ne contient **aucune référence au Québec**. Tout ce qui est québécois vit dans un **profil de région**.
2. **Région = profil de données, pas du code.** Un profil = (a) une grille de zones (GeoJSON/GPKG avec attribut EPSG par zone), (b) une table de CRS candidats (zones + CRS multi-zones type Lambert), (c) des paramètres de décision (seuils). Ajouter une région = ajouter un profil, zéro modification du moteur.
3. **Identifiants de région stables** dès la V1 : `qc` (défaut V1), puis `ca`, etc. Exposés via `--region` dans la CLI. Le défaut est configurable pour que `crszone analyze couche.gpkg` reste court à l'usage.
4. **Templates de rapport indépendants de la région.** Le template HTML reçoit des données (nom des zones, codes, carte) sans logique régionale en dur.
5. **Sorties machine versionnées.** Le format de la sortie `--json` et du journal de décision porte un champ `schema_version` dès la V1 — les scripts des utilisateurs ne casseront pas quand le format évoluera.
6. **Famille de datum respectée.** La logique « recommander un CRS de la même famille de datum que l'entrée, CSRS par défaut » (cf. `DATA_REFERENCE.md`) est un mécanisme générique, pas une règle québécoise — elle resservira telle quelle pour NAD83/WGS84/ITRF ailleurs.
7. **Ni nom de famille de datum, ni libellé régional en dur dans le noyau.** Les familles, leurs politiques et les libellés de systèmes de zones sont des données de profil (étend le principe 1 au vocabulaire, pas seulement aux données géographiques).

---

## 2. V1 — Québec (périmètre actuel)

Rappel du périmètre défini au cadrage initial du projet : zones MTM 2–10 + Québec Lambert, CLI (`analyze` / `apply` / `grid`), formats vectoriels GPKG/SHP/GeoJSON, rapport HTML auto-porté, sortie `--json`, journal de décision, grille MTM committée dans le dépôt.

Décisions V1 actées en cours de cadrage (à formaliser dans `SPEC.md`) :

| Décision | Choix V1 | Alternative reportée (voir §3/§4) |
|---|---|---|
| Rapport détaillé | **HTML auto-porté** (template Jinja2, CSS inline, carte PNG base64) | PDF via weasyprint (V1.x) |
| Sémantique multi-zones | **Affectation par majorité** (surface/longueur dominante par zone), entités intactes | Découpe géométrique exacte `--split exact` (V1.x) ; centroïde écarté (centroïde possiblement hors de l'entité) |
| Datum | **NAD83(CSRS)** par défaut (EPSG 2944–2952, 6622) ; série NAD83 d'origine reconnue en entrée et respectée en sortie | — |
| Grille MTM | **Committée** dans le dépôt (GeoJSON, généré par `crszone grid`, régénérable) | — |
| Entrées NAD27 | **Reconnues en entrée, jamais reconduites en sortie** : recommandation CSRS avec transformation NTv2 explicite, confirmée par l'utilisateur et journalisée (`DATA_REFERENCE.md` §1.5 et §6.1) | — |

---

## 3. V1.x — améliorations court terme (après V1 fonctionnelle)

| Idée | Détail | Origine / justification |
|---|---|---|
| `--pdf` | Rendu PDF du rapport en réutilisant le même template HTML/CSS (weasyprint) ; s'appuiera sur la maquette du rapport HTML pensée impression. | Demande utilisateur final « document figé » ; reporté pour éviter la dépendance lourde en V1. |
| `--split exact` | Découpe géométrique réelle à la frontière de fuseau (aucune perte de couverture par zone). | Complément de l'affectation par majorité ; utile pour les couches de couverture continue (occupation du sol). |
| Gestion CRS indéfini enrichie | Au-delà de `--assume-crs` : heuristique de plausibilité (l'emprise tombe-t-elle au Québec si on suppose EPSG:4326 ? un MTM ? etc.) avec suggestion à l'utilisateur. | Décision ouverte §7 du doc de définition. |
| `--datum csrs` | Changement de famille de datum **explicite** (vieux NAD83 → CSRS) via une vraie transformation (grilles NRCan), transformation utilisée inscrite au journal de décision ; refus si seule une transformation approximative est disponible. | Jamais implicite — cf. `DATA_REFERENCE.md` §6.1 (piège de la transformation nulle). Nécessite la source NRCan (dette bibliographique). |
| Publication PyPI | `pip install crs-zone-toolkit` ; trusted publishing GitHub Actions. | Crédibilité produit. |
| GIF de démo README | Flux analyser → décider → agir enregistré (ex. `vhs` de Charm). | Vitrine du dépôt public. |
| Assouplissements de généralisation | `crs_mesure`/`crs_affichage` explicites au profil ; `familles_preservees` + `famille_defaut` réellement branché ; libellés de système de zones au profil ; TP-41 durci par un profil factice **dissemblable** de `qc`. | Prépare le terrain à la V2 (§1 principe 7, §4) : sortir du code ce qui doit devenir donnée de profil. |
| Performance | Répartition et découpage en `overlay`/STRtree au lieu des doubles boucles. | Anticipe les couches volumineuses avant l'extension multi-région de la V2. |

---

## 4. V2 — Canada

| Idée | Détail | Points d'attention |
|---|---|---|
| **Profils par système de zones** | `ca` (UTM pan-canadien) + profils provinciaux (`on`, `bc`… au fil de la demande), reliés par l'auto-détection ; **un profil = un système**, jamais deux grilles recouvrantes. Pour le Québec, la grille `ca` est déjà sourcée [REF-01] : fuseaux 17–21, NAD83 26917–26921, CSRS 2958–2962 (bornes vérifiées [REF-09]) ; à compléter (7N–22N) pour le reste du Canada. | Le chargeur exige des bandes contiguës et non recouvrantes : un méga-profil multi-systèmes échouerait au chargement. Première vraie preuve que l'architecture « profil » tient : ne doit demander **aucun** changement moteur. |
| Systèmes provinciaux | L'Ontario utilise aussi le MTM (zones 8–17) ; d'autres provinces ont leurs Lambert/Albers (ex. BC Albers EPSG:3005, Alberta 10-TM). | Codes à valider systématiquement contre le registre EPSG avant intégration (cf. `references.md`). |
| **Table de familles de datum au profil** | Code géographique, alias de détection, politique `preservee`/`defaut`/`entree_seule`, `grille_obligatoire`, libellés, note de rapport ; par fuseau, `codes = {famille: epsg}` au lieu des trois colonnes actuelles. | Donnée pivot de la V2 : condition pour que §1 principe 7 (aucun nom de famille en dur) tienne. |
| **Validation de complétude des familles au chargeur** | `lambert_epsg` est appelé en pleine analyse (comparaison de distorsion) : un profil V2 dont `multi_zones` n'aurait pas la famille d'entrée échouerait tard, au milieu du travail, alors que le chargeur (`regions/loader.py`, qui exige déjà `multi_zones['csrs']`) pourrait refuser dès le chargement — immédiatement actionnable. | À faire au moment de la table de familles (ci-dessus), avec laquelle cette validation partage sa donnée. |
| Grille UTM mondiale (sous-produit) | Extension du générateur de grille : zones UTM 1–60 N/S avec EPSG par zone. | Généralisation directe de `crszone grid`. |
| Auto-détection de région | Si l'emprise tombe dans une région à profil connu, la proposer automatiquement (plus besoin de `--region`). | Nécessite un index des emprises de profils. |
| **`crszone doctor`** | Diagnostic de l'environnement : grilles PROJ présentes/absentes par famille du profil, versions. | Outil de support ; dépend de la table de familles au profil pour savoir quelles grilles vérifier. |
| **API publique documentée** | `from crs_zone_toolkit import analyze` sans passer par la CLI ; prérequis du plugin QGIS (remontée du backlog §6, cf. adaptateurs SIG). | Aucun code moteur dupliqué, aucune dépendance à `PyQGIS`/`arcpy` dans le noyau. |
| **Mode lot** | Dossier ou GPKG multi-couches. | — |

---

## 5. V3 — International (Afrique, monde)

| Idée | Détail | Points d'attention |
|---|---|---|
| Profils africains | Ex. systèmes nationaux + UTM ; datums locaux variés (Clarke 1880, Adindan, WGS84…). | La logique « famille de datum » (§1.6) devient centrale : les écarts de datum en Afrique se comptent en dizaines/centaines de mètres, pas en 1–2 m. **Prérequis : la table de familles de datum au profil (§4)** — sans alias de détection au profil, un datum Clarke 1880 retombe en famille « autre » et la garde DT-01 perd son objet là où les écarts sont les plus grands (dizaines à centaines de mètres). |
| Repli UTM générique mondial | Pour toute emprise hors profil connu : recommandation UTM (équivalent maison de `estimate_utm_crs`, mais avec rapport, distorsion et multi-zones). | C'est le mode « monde entier » à moindre coût — pas besoin d'un profil par pays pour être utile partout. |
| i18n des rapports | Rapports FR/EN au minimum. | Prévoir dès la V1 des chaînes de texte regroupées (pas dispersées dans le code). |

---

## 6. Backlog — idées en vrac (non planifiées)

- **`--purpose area`** : quand l'objectif de l'utilisateur est un calcul de **surfaces**, recommander la projection **équivalente** Québec Albers (EPSG:6624) plutôt que la conforme Lambert — découverte de la contre-vérification MRNF (`DATA_REFERENCE.md` §4.2). Généralisable par profil (conforme vs équivalente selon l'usage déclaré).
  > **Confirmé par le test manuel du 2026-08-01 (observation N19).** L'utilisateur, géomaticien, l'a nommé spontanément comme « la chose que je changerais en premier » — c'est le **seul** relevé du test qui touche au moteur de décision plutôt qu'à la restitution. **Le coût en données est nul** : Québec Albers (6623/6624) **et** MTQ Lambert (3797-3799) sont **déjà** au `profil.toml`, sous `[[reconnus_entree]]` — reconnus en entrée, jamais recommandés ; les promouvoir en candidats est une ligne de configuration. Ce qui coûte est le **second axe de décision** : la règle « distorsion d'abord » compare des projections **conformes** sur un seul critère (ppm de distorsion linéaire), et une équivalente ne se compare pas sur cet axe — elle change la question posée, donc exige un recalibrage. **Dépendance à ne pas oublier** : le rapport HTML explique depuis DT-28 qu'« un seul nombre suffit » **parce que les candidats sont tous conformes** ; cette phrase devra être reprise le jour où Albers entre. L'**UTM**, lui, n'est pas au profil du tout et demanderait d'abord d'étendre `DATA_REFERENCE`.
- **Adaptateurs SIG** — plugin QGIS / toolbox ArcGIS (décision explicitement reportée dans le doc de définition — le moteur CLI validé d'abord). Architecture prévue : de simples **adaptateurs pilotants** au-dessus de l'API `analyze()`/`apply()` (SPEC §11), au même titre que la CLI — aucun code moteur dupliqué, aucune dépendance à `arcpy`/`PyQGIS` dans le noyau. En attendant, l'interopérabilité V1 avec ArcGIS et QGIS passe par les **fichiers** (GPKG/SHP/GeoJSON en entrée-sortie) et les codes EPSG, lus identiquement par les deux SIG.
- **Support raster** (GeoTIFF…) : détection/reprojection au-delà du vectoriel. **V3+, non planifié** — autre métier (rééchantillonnage), pas d'affectation majoritaire.
- **Démo web** (page statique ou petit service), reculée à **après le plugin QGIS** — réévaluerait la chaîne design front écartée au registre outillage §2.

---

## 7. Procédure

1. Toute nouvelle idée (conversation, revue, issue GitHub) s'ajoute **ici**, dans la section correspondant à son horizon, avec sa justification.
2. Quand une idée entre en développement, elle sort de ce document vers le plan d'implémentation (workflow Superpowers) ; à la livraison, la SPEC est mise à jour.
3. À chaque décision de conception V1, vérifier les **principes §1** : est-ce qu'on est en train de coder en dur quelque chose qui devra devenir un profil ?

---

> *Registre vivant. La V1 reste petite (Québec seulement) — ce document existe précisément pour que « commencer petit » ne veuille pas dire « repartir de zéro » à chaque extension.*
