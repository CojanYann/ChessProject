"""Étape 1 : télécharge le PGN Lichess si besoin, puis extrait les parties Blitz 3 min en Parquet."""

import time
import warnings

from elo import config
from utils.pgn import download_pgn, read_games


def main():
    if not config.PGN.exists():
        warnings.warn("Téléchargement de ~28 Go : long (souvent > 30 min), et 28 Go de disque nécessaires.")
        download_pgn(config.PGN_URL, config.PGN)

    t0 = time.time()
    games = read_games(config.PGN, n_read=config.N_LUES, time_controls=config.CADENCES)
    games.write_parquet(config.RAW)
    print(f"{games.height} parties gardées sur {config.N_LUES} lues ({time.time() - t0:.0f} s) -> {config.RAW.name}")
