# ChessProject : estimer le niveau d'une partie d'échecs à partir des coups

Projet de data science (cours KIT DS, Télécom Paris) sur les parties publiques de [Lichess](https://database.lichess.org/).

**Question** : en regardant seulement les coups joués et la gestion de la pendule, peut-on estimer le niveau (Elo)
d'une partie de blitz ?

**Résultat** : sur le jeu de test (8 340 parties, joueurs jamais vus à l'entraînement), le meilleur modèle se trompe en
moyenne de **212 points d'Elo**, contre 277 en prédisant toujours la médiane et 322 en prédisant 1500 pour tout le monde
(le point de départ d'un nouveau compte sur Lichess).

---

## 1. Cadrage

Les plateformes d'échecs (Lichess, Chess.com) comme la FIDE estiment le niveau d'un joueur uniquement à partir de ses
**résultats**. Un nouveau compte n'a donc pas de niveau fiable au départ (1500 pour tout le monde sur Lichess), et il faut
de nombreuses parties avant que sa note se stabilise : en attendant, les appariements sont déséquilibrés.

Nous exploitons l'information que ces systèmes ignorent, **la façon de jouer**, pour estimer le niveau d'une partie
(l'Elo moyen des deux joueurs). Le cadrage complet (contexte, métrique, critère de succès, limites, sources) est dans
[`rendu_final/CADRAGE.md`](rendu_final/CADRAGE.md).

**Métrique** : la MAE (erreur absolue moyenne, en points d'Elo), suivie de la RMSE et du R².

## 2. Installation

Python 3.14 et [uv](https://docs.astral.sh/uv/getting-started/installation/) :

```bash
uv sync
```

Sans uv : `pip install -r requirements.txt` puis `pip install -e .` (le code de `src/` s'importe alors partout).
Pour les notebooks, choisir le kernel du `.venv`.

## 3. Reproduire les résultats

Les données (`Data/`) ne sont pas versionnées. Toutes les commandes se lancent depuis la racine du projet.

| étape | commande / fichier | entrée | sortie (`Data/`) |
|---|---|---|---|
| 0. Données | `uv run python rendu_final/prepare_raw.py` | PGN Lichess de sept. 2026 (téléchargé s'il manque, ~28 Go) | `blitz_180_raw_full.parquet` : 557 237 parties |
| 1. Nettoyage | `rendu_final/01_nettoyage.ipynb` | parquet brut | `blitz_180_parties.parquet` : 196 124 parties |
| 2. Features | `rendu_final/02_features.ipynb` (code dans `src/elo/features.py` et `src/elo/features_partie.py`) | parties propres | `blitz_180_features_partie.parquet` |
| 3. Modèles | `rendu_final/03_modeles.ipynb` | features | scores et graphiques |

`prepare_raw.py` lit le PGN en streaming et par morceaux de 100 000 parties, pour ne pas saturer la RAM.

## 4. Démarche et choix

### Données
Les 2 millions premières parties classées de septembre 2026 (environ 16 h de jeu, le 1er septembre), limitées au
**blitz 3 minutes** (180+0 et 180+2) : l'Elo Lichess est propre à chaque cadence, et la pendule n'est comparable qu'à temps égal.

### Nettoyage (`01_nettoyage`)
Chaque anomalie est d'abord **mesurée** (sections 3 à 7, aucune ligne retirée), puis traitée avec un seuil justifié par les données.

| décision | pourquoi |
|---|---|
| retirer les BOT, les parties abandonnées ou en infraction, celles de moins de 20 demi-coups | coups non représentatifs d'un humain |
| retirer les pendules anormales (berserk, temps ajouté) | gestion du temps non comparable |
| écart d'Elo entre les joueurs ≤ 200 | au-delà, l'Elo moyen ne décrit le niveau d'aucun des deux joueurs |
| \|RatingDiff\| ≤ 9 pour les deux joueurs | au-delà, l'Elo est encore provisoire (compte récent) |
| au plus 20 parties par joueur, doublons exacts retirés | éviter qu'une poignée de joueurs très actifs domine les données |
| annotations `?!`, `??` retirées des coups, `%eval` non utilisé | elles n'existent que dans les parties analysées, surtout chez les joueurs forts : fuite d'information |
| split train / valid / test (70 / 15 / 15) **par joueur** | un joueur garde le même Elo et le même style toute la journée : sans cela, le modèle reconnaîtrait le joueur au lieu d'estimer son niveau |

Le split par joueur a un coût : seules les parties dont les deux joueurs tombent dans le même groupe sont gardées
(170 806 parties écartées). Douze contrôles automatiques vérifient la table finale (clés uniques, pas de joueur dans deux
groupes, parties légales rejouées avec `python-chess`…). Détail dans [`rendu_final/RECAP_dataset.md`](rendu_final/RECAP_dataset.md).

### Features (`02_features`)
Calculées uniquement à partir des coups et de la pendule (jamais l'Elo, le résultat ou `RatingDiff`), pour chaque couleur
puis moyennées sur la partie. Cinq familles : **pendule**, **coups** (captures, échecs, roque…), **ouverture**
(profondeur de théorie), **matériel** (partie rejouée avec `python-chess`) et **partie** (longueur, cadence).
Toute l'analyse (corrélations, redondance, sélection) est faite sur le train ; le test n'est pas ouvert.

### Modèles (`03_modeles`)
Deux références (1500 pour tout le monde, médiane du train), une régression Ridge et un HistGradientBoosting.
Le modèle est choisi sur le valid ; le test n'est utilisé **qu'une seule fois**, à la fin.

## 5. Résultats

| modèle | MAE valid (IC 95 %) | MAE test | R² test |
|---|---|---|---|
| 1500 pour tout le monde | 313,3 | 322,4 | −0,30 |
| médiane du train | 271,9 | 276,6 | 0,00 |
| Ridge | 224,7 (221,2 – 228,2) | | |
| **HistGradientBoosting** | **213,5** (209,9 – 217,1) | **212,2** | **0,40** |

- Le boosting gagne **64 points** sur la médiane et **110 points** sur « 1500 pour tout le monde ».
- La MAE du test est très proche de celle du valid : pas de sur-ajustement au valid.
- L'erreur dépend fortement du niveau : environ 130 points vers 1600, mais 450 vers 800 et 530 vers 2400.
  Le modèle ramène ses prédictions vers le centre (régression vers la moyenne) : une seule partie ne suffit pas à
  reconnaître avec certitude un joueur très faible ou très fort.
- Les features les plus utiles : la part de coups rapides, la réponse des Noirs à l'ouverture, la régularité du temps de
  réflexion, le déséquilibre de matériel et la profondeur de théorie.

## 6. Limites et pistes

- **Une seule journée** de blitz 3 minutes, et une population filtrée (pas de comptes provisoires, peu de tournois).
- **Pas de mesure directe de la qualité des coups** (pas de moteur d'échecs) : le matériel n'en est qu'une approximation.
- Pistes : estimer le niveau d'un **joueur** sur plusieurs parties (utile pour repérer un compte mal classé ou un smurf),
  ajouter d'autres jours de données, des features d'échiquier plus fines.

## 7. Organisation du dépôt

| dossier | contenu |
|---|---|
| `rendu_final/` | **le rendu** : script de données, les 3 notebooks, cadrage et fiche du dataset |
| `src/elo/`, `src/utils/` | code réutilisé par le rendu (lecture du PGN, calcul des features) |
| `archives/` | première approche (prédire l'Elo d'un joueur, 1 ligne par joueur et par partie), abandonnée : voir [`archives/README.md`](archives/README.md) |
| `par_personne/` | brouillons et explorations individuelles |
