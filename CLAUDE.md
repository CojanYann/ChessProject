# ChessProject — prédire l'Elo à partir des coups

Projet ML (cours KIT DS, Télécom Paris). But = **apprendre** plus qu'avoir le meilleur modèle.
Cible : Elo de chaque joueur (1 ligne par joueur et par partie, à confirmer).

## Préférences
- Français. **Très simple**, pas à pas, notebooks courts, pas d'overengineering ; supprimer l'inutile en mettant à jour.
- Discuter avant de coder quand l'utilisateur le demande. Choix justifiés par les données plutôt qu'arbitraires.
- Polars (pas pandas). Pas de Stockfish. Pas de graphes pour l'instant.

## Stack
uv, Python 3.14, polars 2.0, pyarrow, zstandard ; ipykernel en dev. `uv run ...`

## Données
- `Data/lichess_db_standard_rated_2026-09.pgn.zst` : 28 Go, Lichess sept. 2026, ~2.2M parties/jour,
  ordre chronologique, lecture streaming ~27 s / 1M parties. `Data/` dans `.gitignore`.
- PGN : en-têtes `[Clé "valeur"]` puis **une ligne** de coups `1. e4 { [%clk 0:02:00] } 1... c5 { ... }`.
  `%clk` = temps restant ; `%eval` rare. Titres : `BOT` à exclure.
- `Data/sample_10k.parquet` (notebook 01), `Data/blitz_180_raw.parquet` (notebook 02 : 2M premières parties
  ≈ 24h du 1er sept., filtrées 180+0 / 180+2 → 557k parties).

## Code
- `src/utils/pgn.py` : `open_pgn`, `read_games(path, n_read, time_controls)` -> DataFrame (en-têtes, Elo int, `moves`, `n_moves`).
- `notebooks/01_exploration.ipynb` : structure du fichier.
- `notebooks/02_preparation.ipynb` : choix cadence + seuil de coups minimum.

## Stratégie (feuille de route)
Polars pour tout le tabulaire/texte/pendule ; python-chess seulement pour features d'échiquier, sur données déjà filtrées.
1. Préparation : 1 cadence, filtres (coups min, BOT, Abandoned/Rules infraction, Elo provisoires via |RatingDiff|), 1 ligne/joueur.
2. Baselines : constante (MAE ~320-350), puis régression linéaire simple.
3. Features texte SAN + pendule (Polars). 4. Features échiquier (python-chess). 5. Séquences : n-grammes TF-IDF, puis réseau séquentiel.
Comparer la MAE à chaque étape. Anti-fuite : pas d'Elo adverse ni RatingDiff en feature ; split train/test par joueur.

## État actuel (étape 1, en cours)
- 180+0 : 379k parties, Elo std 350 ; 180+2 : 179k, std 365. Choix en attente.
- Parties courtes : % Time forfeit ~50% à 1 coup/joueur, se stabilise vers ~10-13% à partir de ~8-10 coups/joueur.
  Moins de 10 coups/joueur = ~4% des parties. Seuil à valider plus tard via erreur du modèle vs nb de coups.
