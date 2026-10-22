# ChessProject — prédire l'Elo à partir des coups

Projet ML (cours KIT DS, Télécom Paris). But = **apprendre** plus qu'avoir le meilleur modèle.
Cible : Elo de chaque joueur (1 ligne par joueur et par partie).

## Préférences
- Français. **Très simple**, pas à pas, notebooks courts, pas d'overengineering ; supprimer l'inutile en mettant à jour.
- Discuter avant de coder quand l'utilisateur le demande. Choix justifiés par les données plutôt qu'arbitraires.
- Polars (pas pandas). Pas de Stockfish. Graphes : matplotlib + plotly (pré-agréger avec Polars avant plotly).

## Stack
uv, Python 3.14, polars 2.0, pyarrow, zstandard, matplotlib, plotly ; ipykernel + nbformat en dev. `uv run ...`

## Données
- `Data/lichess_db_standard_rated_2026-09.pgn.zst` : 28 Go, Lichess sept. 2026, ~2.2M parties/jour,
  ordre chronologique, lecture streaming ~27 s / 1M parties. `Data/` dans `.gitignore`.
- PGN : en-têtes `[Clé "valeur"]` puis **une ligne** de coups `1. e4 { [%clk 0:02:00] } 1... c5 { ... }`.
  `%clk` = temps restant ; `%eval` rare. Titres : `BOT` à exclure.
- `Data/blitz_180_raw.parquet` (notebook 02 : 2M premières parties ≈ 24h du 1er sept., filtrées 180+0 / 180+2 → 557k parties).
- `Data/blitz_180_joueurs.parquet` (notebook 01) : table propre, 1 ligne/joueur-partie (1.02M) : `game_id, joueur, couleur, elo,
  rating_diff, cadence, score, termination, eco, san` (liste), `clk` (liste, secondes), `a_eval`.

## Code
- `src/utils/pgn.py` : `open_pgn`, `read_games(path, n_read, time_controls)` -> DataFrame (en-têtes, Elo int, `moves`, `n_moves`) ;
  `parse_moves(df)` : `Movetext` brut -> `moves` = liste de {san, clk, eval}.
- `notebooks/01_exploration.ipynb` : nettoyage + 1 ligne/joueur + exploration des features vs Elo (lit `blitz_180_raw`).
- `notebooks/02_preparation.ipynb` : choix cadence + seuil de coups minimum.

## Stratégie (feuille de route)
Polars pour tout le tabulaire/texte/pendule ; python-chess seulement pour features d'échiquier, sur données déjà filtrées.
1. Préparation : 1 cadence, filtres (coups min, BOT, Abandoned/Rules infraction, Elo provisoires via |RatingDiff|), 1 ligne/joueur.
2. Baselines : constante (MAE 281), puis régression linéaire simple.
3. Features texte SAN + pendule (Polars). 4. Features échiquier (python-chess). 5. Séquences : n-grammes TF-IDF, puis réseau séquentiel.
Comparer la MAE à chaque étape. Anti-fuite : pas d'Elo adverse ni RatingDiff en feature ; split train/test par joueur.

## État actuel (étape 1 faite, notebook 01)
- On garde 180+0 et 180+2 (cadence = variable ; 180+2 ≈ 80 pts plus bas en moyenne).
- Filtres partie : BOT, Abandoned/Rules infraction, < 20 demi-coups. Filtres joueur : |RatingDiff| > 15 (provisoire),
  pendule anormale (berserk = départ 90 s, temps ajouté = remontée > incrément).
- Baseline médiane : MAE = 281. Corr. Elo blanc/noir = 0.96 (fuite). Même joueur : Elo std ~6 pts/jour -> split par joueur.
- Meilleures features (Spearman |ρ| ≤ 0.26) : temps sur 10 premiers coups, % coups ≤ 1 s, n_coups, % captures, roque.
  Plusieurs relations en U. `score` ≈ inutile.
- `%eval` : 9 % des lignes, très biaisé vers les forts (>60 % au-dessus de 2600). Traitement à décider.
