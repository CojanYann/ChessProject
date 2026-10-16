# ChessProject

Prédire l'Elo d'un joueur à partir des coups de ses parties (données Lichess).

## Installation

1. Installer [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Dans le dossier du projet :
   ```bash
   uv sync
   ```
   Ça crée le `.venv` et installe tout (Python 3.14, polars, ...) d'après `uv.lock`.
3. Lancer un script : `uv run python mon_script.py`.
   Pour les notebooks, choisir le kernel `.venv` dans VS Code / Jupyter.

Ajouter une librairie : `uv add nom_lib` (puis commit `pyproject.toml` et `uv.lock`).
Ne jamais faire `pip install` à la main.

## Données

Les données sont dans `Data/` (pas sur git, trop lourd).
Télécharger le fichier `.pgn.zst` sur [database.lichess.org](https://database.lichess.org/) et le mettre dans `Data/`.

## Organisation du repo

| Dossier | Contenu | Sur git ? |
|---|---|---|
| `notebooks/` | Notebooks **communs**, propres, validés par le groupe | Oui |
| `src/` | Le vrai code : fonctions réutilisables, modifs importantes | Oui |
| `notebook<prenom>/` | Ton brouillon perso (tests, essais) | **Non** |
| `Data/` | Données | **Non** |

## Règles

- **On ne push pas ses notebooks perso.** Crée ton dossier `notebook<prenom>/` et ajoute-le au `.gitignore` (ex. `/notebookyann`).
- Le code utile trouvé dans ton brouillon → on le met **dans `src/`** sous forme de fonction, puis on l'importe.
- Un notebook dans `notebooks/` = court, qui tourne de haut en bas, et dont le groupe est d'accord.
- Avant de push : `git pull`, vérifier que ça tourne, puis commit avec un message clair.
