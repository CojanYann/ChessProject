# ChessProject — prédire l'Elo à partir des coups

Projet ML (cours KIT DS, Télécom Paris). Cible : Elo de chaque joueur (1 ligne par joueur et par partie).

## Priorité n°1 : que les étudiants comprennent et apprennent
Le plus important est que les étudiants du projet **comprennent** ce qui est fait et **apprennent**, bien avant la
performance du modèle et tout le reste. Concrètement : expliquer chaque choix et chaque concept simplement (avec un
exemple), privilégier le code lisible au code astucieux, montrer les erreurs et les fausses bonnes idées (et pourquoi),
répondre aux questions avant d'avancer. Un gain de MAE qu'ils ne comprennent pas ne vaut rien.

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
- `Data/blitz_180_raw.parquet` (notebook 00, ~4 min : 2M premières parties ≈ 24h du 1er sept., filtrées 180+0 / 180+2
  → 557k parties ; `moves` = liste de {san, clk, eval}).
- `Data/blitz_180_joueurs.parquet` (notebook 01) : table propre, 1 ligne/joueur-partie (1.02M) : `game_id, joueur, couleur, elo,
  rating_diff, cadence, score, termination, eco, san` (liste), `clk` (liste, secondes), `a_eval`.
- `Data/blitz_180_features.parquet` (notebook 03) : `game_id, joueur, elo` + 24 features numériques + 5 catégorielles
  (`couleur, cadence, fin, premier_coup, eco_lettre`).

## Code
Projet installé en éditable (`[build-system]` setuptools, `uv sync`). Pipeline : `uv run python -m elo <étape>|tout`
(~4 min) ; README = rapport avec graphes (`figures/`), `TODO.md` = tâches.
- `src/elo/` : `config.py` (chemins, seuils), `extraction.py`, `nettoyage.py` (filtre_parties, une_ligne_par_joueur,
  filtre_joueurs), `features.py` (PENDULE, COUPS, OUVERTURE, calcule_features), `modeles.py` (charge, split,
  lineaire, boosting, scores, importance_permutation), `figures.py` (PNG du README), `__main__.py` (argparse).
- `src/utils/` : `pgn.py` (download_pgn, open_pgn, read_games, parse_moves), `Move.py` + `chessboard.py` (collègue).
- Notebooks 00-04 = analyse détaillée ; 03 et 04 importent `elo.features` / `elo.modeles` ; 01 garde son code
  pas à pas (miroir de `nettoyage.py`). Notebooks générés via scripts dans le scratchpad (ne pas régénérer à l'aveugle).

## Stratégie (feuille de route)
Polars pour tout le tabulaire/texte/pendule ; python-chess seulement pour features d'échiquier, sur données déjà filtrées.
1. Préparation : 1 cadence, filtres (coups min, BOT, Abandoned/Rules infraction, Elo provisoires via |RatingDiff|), 1 ligne/joueur.
2. Baselines : constante (MAE 281), puis régression linéaire simple.
3. Features texte SAN + pendule (Polars). 4. Features échiquier (python-chess). 5. Séquences : n-grammes TF-IDF, puis réseau séquentiel.
Comparer la MAE à chaque étape. Anti-fuite : pas d'Elo adverse ni RatingDiff en feature ; split train/test par joueur.

## État actuel (étapes 1, 2, 3 faites ; prochain : simplifier les features, puis échiquier / n-grammes / evals)
- On garde 180+0 et 180+2 (cadence = variable ; 180+2 ≈ 80 pts plus bas en moyenne).
- Filtres partie : BOT, Abandoned/Rules infraction, < 20 demi-coups. Filtres joueur : |RatingDiff| > 15 (provisoire),
  pendule anormale (berserk = départ 90 s, temps ajouté = remontée > incrément).
- Baseline médiane : MAE = 281. Corr. Elo blanc/noir = 0.96 (fuite). Même joueur : Elo std ~6 pts/jour -> split par joueur.
- Meilleures features (Spearman |ρ| ≤ 0.26) : temps sur 10 premiers coups, % coups ≤ 1 s, n_coups, % captures, roque.
  Plusieurs relations en U. `score` ≈ inutile.
- `%eval` : 9 % des lignes, très biaisé vers les forts (>60 % au-dessus de 2600). Traitement à décider.
- Notebook 03 : top |ρ| t_ouverture 0.27, pct_rapides 0.25, cv_temps 0.23, coup_t_max 0.16, n_coups 0.15.
  Inutiles : pct_pions, pct_dame, n_promotions, t_finale. Cadence décale toute la pendule (180+2 : +1.2 s/coup ouverture).
  `fin` : mats chez les faibles, abandons/nulles chez les forts ; `fin = inconnu` = artefact du filtrage -> manquant.
  Max redondance |ρ| 0.79 (pct_longs/t_milieu). Métriques prévues : MAE (principale), R², MAE par tranche d'Elo.
- Notebook 04 (test 205k lignes, 30k joueurs) : MAE médiane 283, linéaire 249 (R² 0.22), HGB 241 (R² 0.27).
  Forte régression vers la moyenne (750 -> prédit ~1400, 2650 -> ~1950) : MAE ~120 au centre, 600-700 aux extrêmes.
  Importance : cv_temps, pct_rapides, t_ouverture, premier_coup, temps_restant_fin, fin, pct_captures ; ~15 features < 1 pt.
  Linéaire : retirer pct_pions (pct_* somment à ~1 -> colinéarité). Moyenner k parties : plateau ~207 dès k=5
  -> biais, pas bruit : il faut des features de qualité des coups. Seuil 10 coups validé (gain vs médiane stable).
