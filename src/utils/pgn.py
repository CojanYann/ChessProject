"""Lecture du PGN Lichess (.pgn.zst) en streaming -> DataFrame Polars (1 ligne par partie)."""

import io
import urllib.request

import polars as pl
import zstandard


def download_pgn(url, path):
    """Télécharge `url` dans `path` par morceaux de 1 Mo, en affichant la progression tous les Go.
    Écrit dans `path.part` puis renomme à la fin : un téléchargement interrompu ne laisse pas un faux fichier complet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        done, next_print = 0, 1e9
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if done >= next_print:
                print(f"{done / 1e9:.0f} / {total / 1e9:.0f} Go", flush=True)
                next_print += 1e9
    tmp.rename(path)


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
