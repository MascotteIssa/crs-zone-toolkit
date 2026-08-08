# `scripts/` — outils de mainteneur

Ce dossier n'est **pas distribué** (exclu du sdist, cf. `pyproject.toml`) : ce sont
des outils de développement, pas une surface publique du paquet.

## `regenerer_demos.py` — DT-17

Régénère les ressources de démonstration du README depuis le **moteur réel**
(`crs_zone_toolkit.analyze` puis `report`) — jamais depuis un HTML recopié :

- l'extrait terminal du README (« En trente secondes »), entre les marqueurs
  `<!-- extrait:debut -->` / `<!-- extrait:fin -->`
- `docs/exemple_rapport.html`
- `docs/images/rapport-{clair,sombre}.png` et `rapport-distorsion-{clair,sombre}.png`
- `docs/images/demo.gif`

### Quand le lancer

Après **toute** modification touchant :

- le gabarit du rapport (`src/crs_zone_toolkit/templates/rapport.html.j2`) ;
- la règle de décision (`core/analysis._decide`) ;
- le résumé terminal (`affichage.resume_analyse` / `core/messages.py`).

Sans quoi le README montre un outil qui n'existe plus (DT-17)
— c'est arrivé une fois : les Tasks 3-4 de la
Phase B ont changé le résumé terminal, périmant `demo.gif` du jour au lendemain,
et une deuxième fois pour l'extrait terminal du README (revue de branche B,
non couvert par le script avant la Phase C, tâche 4).

### Prérequis

- Une couche de démonstration réelle. Par défaut, celle utilisée en J7 :
  `tests/user_test/data/bdat/regio_s.shp` (« 21 régions administratives du
  Québec », NAD83, multi-fuseaux). **Ce chemin n'existe pas après un simple
  `git clone`** : `tests/user_test/` est hors du périmètre publié — la liste
  blanche de `publier_release.py` ne le retient pas, et les données réelles du
  test manuel ne sont de toute façon pas redistribuées. Fournissez la vôtre
  avec `--couche`, ou procurez-vous la même (« Découpages administratifs »,
  Données Québec, CC-BY 4.0 — `docs/DATA_REFERENCE.md` §6.2).
- `playwright` et `Pillow`, **hors dépendances du paquet** (outil de
  mainteneur, comme en J7) :

  ```bash
  uv pip install playwright pillow
  ```

  Les binaires Chromium sont en général déjà en cache
  (`%LOCALAPPDATA%\ms-playwright` / `~/.cache/ms-playwright`). Ne lancez
  `playwright install chromium` (télécharge ~300 Mo) que si le script échoue
  avec « Executable doesn't exist » — et si ça arrive, essayez d'abord de
  figer une version de `playwright` compatible avec la révision déjà en
  cache (le message d'erreur indique la révision attendue ; `browsers.json`
  du paquet installé l'indique aussi) plutôt que de télécharger à nouveau.

### Usage

```bash
uv run python scripts/regenerer_demos.py --quoi tout
uv run python scripts/regenerer_demos.py --quoi extrait     # l'extrait README, sans Playwright
uv run python scripts/regenerer_demos.py --quoi exemple     # le moins coûteux
uv run python scripts/regenerer_demos.py --quoi captures    # dépend d'« exemple »
uv run python scripts/regenerer_demos.py --quoi gif         # le plus long
```

`--quoi extrait` remplace le contenu entre les marqueurs `<!-- extrait:debut -->`
/ `<!-- extrait:fin -->` du README par la sortie réelle de
`crszone --region <région> analyze <couche>` (console Rich à largeur fixe,
sans couleur — ne dépend pas de Playwright, seul lui échoue bruyamment si les
marqueurs sont absents du README). Idempotent : deux exécutions successives ne
changent rien (le nom du rapport HTML affiché vient d'un horodatage figé dans
le script, pas de `datetime.now()`).

`--couche <chemin>` et `--region <id>` permettent de changer la couche/le
profil de démonstration.

### Ce que le script ne fait pas

Il ne force rien : rien n'échoue la CI si les ressources dérivent (DT-17
reste **ouverte, outillée** — pas résorbée). Il échoue **bruyamment** (message
explicite, aucune ressource modifiée) si la couche source est absente ou si
le rapport attendu par `--quoi captures` n'a pas encore été régénéré.

## `publier_release.py` — Phase D

Prépare le snapshot du dépôt « vitrine » public `crs-zone-toolkit` depuis le
dépôt de développement privé. Le périmètre est une **liste blanche
explicite** (`PERIMETRE_VITRINE`, en tête de fichier) : un fichier nouveau au
dev n'entre dans la vitrine que si on l'ajoute à cette liste. La fuite d'un
document interne vers GitHub est ainsi impossible par construction — même
principe que DT-19 (rendre la dérive impossible plutôt que la rattraper).

Une seconde table, `RENOMMAGES_VITRINE`, publie un fichier **sous un autre
nom**. Elle sert au `.gitignore` : les deux dépôts n'ignorent pas les mêmes
choses, donc la vitrine reçoit le sien (`packaging/gitignore-vitrine`, copié
sous le nom `.gitignore`) plutôt qu'une copie de celui du dev.

> Corollaire pour PyPI : hatchling ajoute le `.gitignore` du dépôt au sdist
> d'office (`force-include`, hors `include`/`exclude` — l'y exclure ne fait
> rien). L'archive porte donc celui du dépôt **où elle est construite**, ce qui
> confirme la règle déjà en place : `uv build` puis `twine upload` se font
> **depuis le clone vitrine**, jamais depuis le dépôt de développement.

**La vitrine ne s'édite JAMAIS à la main** : toute correction se fait au
dépôt dev, puis se republie en relançant ce script.

### Usage

```bash
uv run python scripts/publier_release.py --cible ../crs_zone_toolkit_vitrine
```

`--cible` doit être un clone local existant du dépôt vitrine (un dossier
contenant un `.git`). Le script vide la cible (sauf `.git/`, `dist/`,
`.venv/`), copie les fichiers retenus par la liste blanche, puis s'arrête :
la revue du statut git, le commit, le tag et le push restent des gestes
manuels dans le clone cible (l'utilisateur est seul auteur).
