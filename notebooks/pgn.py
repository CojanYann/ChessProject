"""Lecture du PGN Lichess (.pgn.zst) en streaming -> DataFrame Polars (1 ligne par partie)."""

import io

import polars as pl
import zstandard


def open_pgn(path):
    """Ouvre le .pgn.zst en streaming (sans décompresser les 28 Go)."""
    f = open(path, "rb")
    return io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(f), encoding="utf-8")


def read_games(path, n_read, time_controls=None):
    """Lit les `n_read` premières parties ; garde seulement `time_controls` si donné."""
    games, game, n = [], {}, 0
    with open_pgn(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("["):  # en-tête : [Clé "valeur"]
                key, value = line[1:-1].split(" ", 1)
                game[key] = value.strip('"')
            elif line:  # ligne des coups = fin de la partie
                game["Movetext"] = line
                if time_controls is None or game["TimeControl"] in time_controls:
                    games.append(game)
                game = {}
                n += 1
                if n >= n_read:
                    break
    return to_dataframe(games)


def to_dataframe(games):
    """Liste de dicts -> DataFrame avec Elo en entiers et `moves` (liste des coups SAN)."""
    return (
        pl.DataFrame(games)
        .with_columns(
            pl.col("WhiteElo", "BlackElo", "WhiteRatingDiff", "BlackRatingDiff").cast(pl.Int32, strict=False),
            moves=pl.col("Movetext")
            .str.replace_all(r"\{[^}]*\}", "")  # commentaires {...}
            .str.replace_all(r"\d+\.+", "")  # numéros "1." / "1..."
            .str.replace_all(r"(1-0|0-1|1/2-1/2|\*)\s*$", "")  # résultat final
            .str.split(" ")
            .list.eval(pl.element().filter(pl.element() != "")),
        )
        .with_columns(n_moves=pl.col("moves").list.len())
    )
