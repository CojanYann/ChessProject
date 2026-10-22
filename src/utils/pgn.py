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
    """Liste de dicts -> DataFrame (voir `parse_moves`)."""
    return parse_moves(pl.DataFrame(games, infer_schema_length=None))  # None : garde aussi les en-têtes rares


def parse_moves(df):
    """DataFrame avec `Movetext` brut -> Elo en entiers,
    `moves` = liste de {san, clk, eval} (eval = null si absente)."""
    move = pl.element()  # un coup brut, ex. "1. e4 { [%eval 0.17] [%clk 0:03:00] }"
    return (
        df.with_columns(
            pl.col("WhiteElo", "BlackElo", "WhiteRatingDiff", "BlackRatingDiff").cast(pl.Int32, strict=False),
            moves=pl.col("Movetext")
            .str.extract_all(r"\d+\.+ [^ {]+(?: \{[^}]*\})*")  # numéro + coup + commentaires (0, 1 ou plus)
            .list.eval(
                pl.struct(
                    san=move.str.extract(r"\d+\.+ ([^ {]+)", 1),
                    clk=move.str.extract(r"%clk ([\d:]+)", 1),
                    eval=move.str.extract(r"%eval ([^\]\s]+)", 1),
                )
            ),
        )
        .with_columns(n_moves=pl.col("moves").list.len())
        .drop("Movetext")  # tout est maintenant dans `moves`
    )
