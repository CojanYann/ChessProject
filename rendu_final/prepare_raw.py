"""Étape 0 : récupère les données brutes.

Crée Data/blitz_180_raw_full.parquet (2M premières parties du PGN Lichess, cadences 180+0 et 180+2),
en lisant le PGN par morceaux pour ne pas saturer la RAM. Télécharge le PGN s'il est absent (~28 Go).

Lancer depuis la racine du projet : uv run python rendu_final/prepare_raw.py
"""
import shutil
import sys
from pathlib import Path

import polars as pl

RACINE = Path(__file__).resolve().parents[1]
sys.path.append(str(RACINE / "src" / "utils"))
from pgn import download_pgn, open_pgn, parse_moves  # noqa: E402

PGN_URL = "https://database.lichess.org/standard/lichess_db_standard_rated_2026-09.pgn.zst"
PGN = RACINE / "Data" / "lichess_db_standard_rated_2026-09.pgn.zst"
OUT = RACINE / "Data" / "blitz_180_raw_full.parquet"
PARTS = RACINE / "Data" / "raw_parts"
N_READ = 2_000_000          # nombre de parties lues (toutes cadences)
CHUNK = 100_000             # parties lues avant d'écrire un morceau
TIME_CONTROLS = {"180+0", "180+2"}


def flush(games, part):
    """Écrit un morceau de parties en parquet, en gardant le texte brut des coups (`Movetext`)."""
    df = pl.DataFrame(games, infer_schema_length=None)
    parse_moves(df).with_columns(Movetext=df["Movetext"]).write_parquet(PARTS / f"part_{part:03d}.parquet")


def main():
    if not PGN.exists():
        print(f"PGN absent : téléchargement de {PGN_URL} (~28 Go)")
        download_pgn(PGN_URL, PGN)

    PARTS.mkdir(parents=True, exist_ok=True)
    games, game, n, part = [], {}, 0, 0
    with open_pgn(PGN) as f:
        for line in f:
            line = line.strip()
            if line.startswith("["):  # en-tête : [Clé "valeur"]
                key, value = line[1:-1].split(" ", 1)
                game[key] = value.strip('"')
            elif line:  # ligne des coups = fin de la partie
                game["Movetext"] = line
                if game.get("TimeControl") in TIME_CONTROLS:
                    games.append(game)
                game = {}
                n += 1
                if n % CHUNK == 0:
                    if games:
                        flush(games, part)
                        part += 1
                        games = []
                    print(f"{n:,} parties lues", flush=True)
                if n >= N_READ:
                    break
    if games:
        flush(games, part)

    files = sorted(PARTS.glob("*.parquet"))
    pl.concat([pl.scan_parquet(p) for p in files], how="diagonal_relaxed").sink_parquet(OUT)
    shutil.rmtree(PARTS)
    print(OUT, "->", pl.scan_parquet(OUT).select(pl.len()).collect().item(), "parties")


if __name__ == "__main__":
    main()
