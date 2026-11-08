"""Chemins et paramètres du pipeline (un seul endroit pour les changer)."""

from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DATA = RACINE / "Data"
FIGURES = RACINE / "figures"

PGN_URL = "https://database.lichess.org/standard/lichess_db_standard_rated_2026-09.pgn.zst"
PGN = DATA / "lichess_db_standard_rated_2026-09.pgn.zst"
RAW = DATA / "blitz_180_raw.parquet"  # 1 ligne par partie
JOUEURS = DATA / "blitz_180_joueurs.parquet"  # 1 ligne par joueur-partie, nettoyé
FEATURES = DATA / "blitz_180_features.parquet"
PREDICTIONS = DATA / "predictions_test.parquet"
IMPORTANCES = DATA / "importances.parquet"

# Extraction : 2M premières parties (~24 h du 1er sept.), Blitz 3 min seulement
N_LUES = 2_000_000
CADENCES = {"180+0", "180+2"}

# Nettoyage (choix justifiés dans le notebook 01 et le README)
MIN_DEMI_COUPS = 20  # au moins 10 coups par joueur
MAX_RATING_DIFF = 15  # au-delà : Elo provisoire

# Modèles
TEST_SIZE = 0.2
SEED = 0
