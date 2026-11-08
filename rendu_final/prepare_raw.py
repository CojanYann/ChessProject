"""Crée Data/blitz_180_raw_full.parquet par morceaux, sans saturer la RAM.
A lancer depuis la racine du projet : uv run python prepare_raw.py"""
import shutil
import sys
from pathlib import Path

import polars as pl

sys.path.append("src/utils")
from pgn import open_pgn, parse_moves

PGN = Path("Data/lichess_db_standard_rated_2026-09.pgn.zst")
OUT = Path("Data/blitz_180_raw_full.parquet")
PARTS = Path("Data/raw_parts")
N_READ = 2_000_000          # nombre de parties lues (toutes cadences)
CHUNK = 100_000             # parties lues avant d'écrire un morceau
TIME_CONTROLS = {"180+0", "180+2"}

PARTS.mkdir(parents=True, exist_ok=True)
games, game, n, part = [], {}, 0, 0


def flush():
    global games, part
    if games:
        df = pl.DataFrame(games, infer_schema_length=None)
        parse_moves(df).with_columns(Movetext=df["Movetext"]).write_parquet(PARTS / f"part_{part:03d}.parquet")
        part += 1
        games = []


with open_pgn(PGN) as f:
    for line in f:
        line = line.strip()
        if line.startswith("["):
            key, value = line[1:-1].split(" ", 1)
            game[key] = value.strip('"')
        elif line:
            game["Movetext"] = line
            if game.get("TimeControl") in TIME_CONTROLS:
                games.append(game)
            game = {}
            n += 1
            if n % CHUNK == 0:
                flush()
                print(f"{n:,} parties lues", flush=True)
            if n >= N_READ:
                break
flush()

files = sorted(PARTS.glob("*.parquet"))
pl.concat([pl.scan_parquet(p) for p in files], how="diagonal_relaxed").sink_parquet(OUT)
shutil.rmtree(PARTS)
print(OUT, "->", pl.scan_parquet(OUT).select(pl.len()).collect().item(), "parties")
