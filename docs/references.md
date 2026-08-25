# CRS Zone Toolkit : Références bibliographiques (format APA, 7ᵉ édition)

> **Rôle du document.** Bibliographie centralisée du projet : chaque décision technique importante (codes EPSG, choix de datum, choix d’outil, prior art) pointe vers une source vérifiable. Quand un document du projet (SPEC, DATA_REFERENCE, registre outillage, feuille de route) affirme un fait, ce fait doit être traçable ici.
>
> **Conventions.** Citation dans les autres documents : `[REF-xx]`. Notices au format **APA 7ᵉ édition** (adaptation française : « s. d. » = sans date ; date de consultation indiquée car le contenu de ces pages est susceptible d’évoluer, conformément à la règle APA sur les contenus instables). Chaque notice est suivie d’une **annotation** : ce qu’elle justifie dans le projet.
>
> **Note de méthode (2026-07-05).** Les fiches EPSG ont été relevées via les exports machine d’epsg.io (`/{code}.json` PROJJSON et `/{code}.proj4`), pas depuis des résumés de seconde main : un résumé antérieur s’était révélé erroné sur les paramètres du Québec Lambert (cf. erratum, `DATA_REFERENCE.md` §4).
>
> **Version :** 0.2 · **Date :** 5 juillet 2026 · **Statut :** Référence vivante

---

## 1. Sources officielles : géodésie & CRS du Québec

**[REF-01]** Ministère de l’Énergie et des Ressources naturelles, Direction générale de l’information géospatiale. (2020, décembre). *Codes EPSG des projections utilisées au Québec* [document PDF]. Gouvernement du Québec. https://mrnf.gouv.qc.ca/wp-content/uploads/CO_codes_epsg_quebec.pdf
> Source officielle québécoise n° 1. **Contre-vérification ligne à ligne effectuée le 2026-07-05** (résultats : `DATA_REFERENCE.md` §7) : confirme le Québec Lambert (46°/60°, MC −68,5°) et les fuseaux 3–10 ; **tranche le fuseau 2** (32182/26899, MC −56°, plutôt que SCoPQ 2944) ; apporte NAD27, MTQ Lambert, Québec Albers et les codes UTM 17–21. Auteur sous son nom de 2020 (MERN, devenu MRNF).

**[REF-02]** MapTiler. (s. d.). *NAD83(CSRS) / SCoPQ zone 2* (EPSG:2944) [fiche du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, à l’adresse https://epsg.io/2944
> Zone 2 québécoise : nom officiel « SCoPQ zone 2 » (et non « MTM »), méridien central −55,5°, emprise « Québec à l’est de 57°O ». Fonde la moitié du « piège de la zone 2 » (`DATA_REFERENCE.md` §2).

**[REF-03]** MapTiler. (s. d.). *NAD83(CSRS) / MTM zones 3 à 10* (EPSG:2945 à EPSG:2952) [fiches du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, aux adresses https://epsg.io/2945 … https://epsg.io/2952
> Série CSRS complète : méridiens centraux (−58,5° à −79,5°, pas de 3°), bandes de longitudes, paramètres communs (k₀ = 0,9999 ; faux Est 304 800 m ; GRS80). Alimente la table maîtresse de `DATA_REFERENCE.md` §2–3. Les emprises confirment aussi le débordement des zones 8–10 en Ontario (pertinent pour la V2, feuille de route §4).

**[REF-04]** MapTiler. (s. d.). *NAD83 / MTM zones 2 à 10* (EPSG:32182 à EPSG:32190) [fiches du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, aux adresses https://epsg.io/32182 … https://epsg.io/32190
> Série NAD83 d’origine, reconnue en entrée par l’outil. **EPSG:32182 (« MTM zone 2 », méridien central −56°) est une zone terre-neuvienne, pas l’équivalent de la SCoPQ zone 2 québécoise**, l’autre moitié du piège de la zone 2. Les chaînes proj4 de cette série portent une transformation nulle (`+towgs84=0,0,0`), preuve utilisée en `DATA_REFERENCE.md` §6.1.

**[REF-05]** MapTiler. (s. d.). *NAD83 / Quebec Lambert* (EPSG:32198) [fiche du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, à l’adresse https://epsg.io/32198
> Paramètres vérifiés du Québec Lambert : latitude d’origine 44°N, méridien central −68,5°, parallèles standards 60°N et 46°N (corrige un résumé de recherche erroné, cf. erratum `DATA_REFERENCE.md` §4).

**[REF-06]** MapTiler. (s. d.). *NAD83(CSRS)v2 / Quebec Lambert* (EPSG:6622) [fiche du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, à l’adresse https://epsg.io/6622
> Code Lambert moderne (nom officiel avec « v2 ») ; remplace 32198 pour toute précision meilleure que 2 m → fonde la règle « CSRS par défaut » (`DATA_REFERENCE.md` §1).

**[REF-07]** International Association of Oil & Gas Producers. (s. d.). *MTM Quebec zone 2 (conversion 17700)* [entrée du EPSG Geodetic Parameter Dataset]. EPSG.org. Consulté le 5 juillet 2026, à l’adresse https://epsg.org/conversion_17700/MTM-Quebec-zone-2.html
> Paramètres de conversion MTM au niveau du registre canonique (source amont d’epsg.io).

**[REF-08]** MapTiler. (s. d.). *NAD83(CSRS)* (EPSG:4617) et *NAD83* (EPSG:4269) [fiches du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, aux adresses https://epsg.io/4617 et https://epsg.io/4269
> CRS géographiques des deux familles de datum. La remarque d’EPSG:4617 (« regroupe toutes les versions CSRS ≥ v2, précision ≈ 1 m ») quantifie l’écart entre familles (`DATA_REFERENCE.md` §1 et §5).

**[REF-09]** MapTiler. (s. d.). *Fiches EPSG:26899 (NAD83(CSRS) / MTM zone 2), EPSG:3797–3799 (MTQ Lambert), EPSG:6623–6624 (Quebec Albers), EPSG:32082 et 32098 (NAD27), EPSG:4267 (NAD27), EPSG:26917/26921 et 2958/2962 (UTM)* [fiches du registre EPSG]. epsg.io. Consulté le 5 juillet 2026, aux adresses https://epsg.io/26899 (et codes cités)
> Vérification des codes supplémentaires apportés par [REF-01] : 26899 = MTM zone 2 CSRS (MC −56°, même définition que 32182) → résout le piège du fuseau 2 ; MTQ Lambert (46°/50°, MC −70°, faux Est 800 000 m) → explique l’erratum du Québec Lambert et alimente `DATA_REFERENCE.md` §4.2 ; les chaînes proj4 NAD27 portent `+nadgrids=ca_nrc_ntv2_0.tif` → preuve de la grille NTv2 (`DATA_REFERENCE.md` §6.1) ; codes UTM validés aux bornes (17N, 21N) pour la V2.

**[REF-14]** Ressources naturelles Canada. (s. d.). *About the Canadian Spatial Reference System* [page web]. Gouvernement du Canada. Consulté le 5 juillet 2026, à l’adresse https://natural-resources.canada.ca/science-data/science-research/geomatics/geodetic-reference-systems/canadian-spatial-reference-system-csrs
> Source fédérale officielle sur le CSRS : distinction NAD83(Original) / NAD83(CSRS), époques et grille de vitesses, et surtout l’outil **NTv2** (« horizontal transformation between NAD27, ATS77, NAD83(Original), and NAD83(CSRS) reference frames using binary grid shift files ») et l’outil TRX. Fonde `DATA_REFERENCE.md` §6.1 et la future option `--datum csrs`. Solde la dette NRCan (2026-07-05).

**[REF-15]** Ministère des Ressources naturelles et des Forêts. (2026). *Découpages administratifs* [jeu de données, licence CC-BY 4.0]. Données Québec. Consulté le 5 juillet 2026, à l’adresse https://www.donneesquebec.ca/recherche/dataset/decoupages-administratifs
> Limite administrative du Québec pour la découpe de la grille (`SPEC.md` §6) : SDA du MRNF, échelles 1/20 000 et 1/100 000, formats SHP/FGDB/GPKG, mise à jour mensuelle. **Licence CC-BY 4.0 → la grille dérivée est redistribuable dans le dépôt public avec attribution** (citation recommandée fournie sur la fiche). Pour la découpe, la version 1/100 000 suffit. Solde la dette « limite administrative » (2026-07-05).

## 2. Prior art : pourquoi cet outil a une raison d’exister

**[REF-10]** GeoPandas development team. (s. d.). *GeoDataFrame.estimate_utm_crs* [documentation logicielle]. GeoPandas. Consulté le 5 juillet 2026, à l’adresse https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.estimate_utm_crs.html
> Prior art le plus proche : estime un CRS **UTM uniquement** depuis l’emprise. Ne couvre ni MTM, ni Lambert, ni rapport, ni multi-zones → argument de positionnement à citer dans le README.

**[REF-11]** GeoPandas development team. (s. d.). *Managing projections* [documentation logicielle]. GeoPandas. Consulté le 5 juillet 2026, à l’adresse https://geopandas.org/en/stable/docs/user_guide/projections.html
> Distinction assignation vs reprojection de CRS : clé pour la gestion des couches sans CRS défini.

**[REF-12]** pyproj developers. (s. d.). *pyproj.database.query_crs_info* [documentation logicielle]. pyproj. Consulté le 5 juillet 2026, à l’adresse https://pyproj4.github.io/pyproj/stable/api/database.html
> pyproj sait lister les CRS candidats pour une emprise (`area_of_interest`) : brique interne à réutiliser plutôt que réimplémenter (registre outillage §6).

**[REF-13]** pyproj developers. (s. d.). *pyproj.Proj.get_factors* [documentation logicielle]. pyproj. Consulté le 5 juillet 2026, à l’adresse https://pyproj4.github.io/pyproj/stable/api/proj.html
> Facteurs d’échelle ponctuels/aréaux exacts en tout point : fonde le calcul de distorsion rigoureux du rapport d’analyse (`DATA_REFERENCE.md` §6.3).

**[REF-25]** Esri. (s. d.). *Define a new coordinate system* [documentation logicielle]. ArcGIS Pro. Consulté le 21 août 2026, à l’adresse https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/define-a-new-coordinate-system.htm
> Prior art le plus proche **hors écosystème Python** : « New suggested projected coordinate system » propose une projection d’après l’emprise et la propriété à préserver (surface, distance, forme). La projection produite est **sur mesure**, rangée sous « Custom », donc sans code EPSG standard, argument de positionnement à citer dans le README (l’échange de données québécoises réclame le MTM officiel ou le Québec Lambert).

**[REF-26]** QGIS project. (s. d.). *Working with projections* [documentation logicielle]. QGIS Documentation 3.44. Consulté le 21 août 2026, à l’adresse https://docs.qgis.org/3.44/en/docs/user_manual/working_with_projections/working_with_projections.html
> Établit que QGIS donne accès à « approximately 7,000 known CRSs » et accompagne l’assignation et la transformation. **Aucune recommandation classée ni mesure de distorsion n’y est décrite** ; la formulation du README s’en tient donc à ce que la source énonce, sans affirmer une absence non vérifiable.

## 3. Écosystème & outillage de développement

**[REF-20]** *Registre d’outillage d’un projet interne antérieur* [document interne, non publié]. (2026).
> Décisions héritées : chaîne d’outillage de développement, procédure d’ajout d’un outil, principe de sobriété.

**[REF-21]** GeoPandas development team. (s. d.). *Changelog* [documentation logicielle]. GeoPandas. Consulté le 5 juillet 2026, à l’adresse https://geopandas.org/en/stable/docs/changelog.html
> pyogrio moteur d’E/S par défaut depuis GeoPandas 1.0 (remplace Fiona), choix du registre outillage §5.1. *Pointer la section 1.0 lors de la vérification.*

**[REF-22]** Ramírez, S. (s. d.). *Typer* [documentation logicielle]. Consulté le 5 juillet 2026, à l’adresse https://typer.tiangolo.com/
> Framework CLI retenu (registre outillage §5.1) : sous-commandes `analyze`/`apply`/`grid`, typage des options, `--help` généré.

**[REF-23]** McGugan, W. (s. d.). *Rich* [documentation logicielle]. Read the Docs. Consulté le 5 juillet 2026, à l’adresse https://rich.readthedocs.io
> Rendu terminal retenu (registre outillage §5.1) : tableaux du résumé d’analyse et invites de confirmation d'`apply` (`CLI_UX.md`).

**[REF-24]** Pallets. (s. d.). *Jinja* [documentation logicielle]. Consulté le 5 juillet 2026, à l’adresse https://jinja.palletsprojects.com/en/stable/
> Moteur de template du rapport HTML auto-porté (`SPEC.md` §7).

**[REF-27]** Sirokov, R. (s. d.). *pywebview* [documentation logicielle, version 6.2.1]. Consulté le 25 août 2026, à l’adresse https://pywebview.flowrl.com/
> Fenêtre de l’**interface de bureau** (registre outillage §5.1). La documentation présente pywebview comme une enveloppe légère et multiplateforme autour d’un composant webview, affichant du HTML dans une fenêtre native : c’est ce qui permet de servir `gui/web/index.html` sans embarquer de moteur de rendu. Version documentée identique à la version installée.

**[REF-28]** Goebel, H., Bajo, G., Vierra, D., Cortesi, D., & Zibricky, M. (s. d.). *PyInstaller Manual* [documentation logicielle, version 6.22.2]. Consulté le 25 août 2026, à l’adresse https://pyinstaller.org/en/stable/
> Empaquetage de l’exécutable de bureau (registre outillage §5.2). L’analyse des dépendances y est **statique** : c’est la raison pour laquelle les données du paquet et les sous-modules compilés de `pyogrio` sont déclarés explicitement dans `packaging/crszone-gui.spec` — le premier `.exe` produit échouait faute de cette déclaration.

---

## 4. Procédure

1. **Aucun code EPSG, seuil ou paramètre géodésique codé en dur sans notice ici.** C’est la parade contre le risque d’erreur n° 1 du projet (codes erronés ou hallucinés).
2. Toute nouvelle source : notice APA 7 avec ID stable (`REF-xx`), annotation « ce qu’elle justifie », et date de consultation pour les contenus instables.
3. Préférer les **exports machine** (PROJJSON, proj4, API) aux résumés et synthèses : l’erratum du Québec Lambert en est la démonstration.
4. Si une source contredit une décision prise : le signaler dans le document concerné, pas seulement ici.

---

> *Registre vivant. Une décision non sourcée est une décision fragile.*
