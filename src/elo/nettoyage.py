"""Étape 2 : filtre les parties, passe à 1 ligne par joueur-partie, filtre les joueurs (détails : notebook 01)."""

import polars as pl

from elo import config

_clk = pl.element().struct.field("clk").str.to_time("%H:%M:%S")
EN_SECONDES = _clk.dt.hour().cast(pl.Int32) * 3600 + _clk.dt.minute().cast(pl.Int32) * 60 + _clk.dt.second().cast(pl.Int32)


def filtre_parties(games):
    """Retire les parties avec un BOT, abandonnées ou sanctionnées, et celles de moins de 10 coups par joueur."""
    est_bot = (pl.col("WhiteTitle") == "BOT").fill_null(False) | (pl.col("BlackTitle") == "BOT").fill_null(False)
    return games.filter(
        ~est_bot,
        ~pl.col("Termination").is_in(["Abandoned", "Rules infraction"]),
        pl.col("n_moves") >= config.MIN_DEMI_COUPS,
    )


def un_cote(games, couleur, offset, score):
    """Table d'une couleur : 1 ligne par partie, avec seulement les coups (1 demi-coup sur 2) de ce joueur."""
    coups = pl.col("moves").list.gather_every(2, offset)
    return games.select(
        game_id=pl.col("Site").str.extract(r"lichess\.org/(\w+)"),
        joueur=pl.col(couleur),
        couleur=pl.lit(couleur),
        elo=pl.col(f"{couleur}Elo"),
        rating_diff=pl.col(f"{couleur}RatingDiff"),
        cadence=pl.col("TimeControl"),
        score=score,
        termination=pl.col("Termination"),
        eco=pl.col("ECO"),
        san=coups.list.eval(pl.element().struct.field("san")),
        clk=coups.list.eval(EN_SECONDES),
        a_eval=pl.col("moves").list.eval(pl.element().struct.field("eval").is_not_null()).list.any(),
    )


def une_ligne_par_joueur(games):
    """2 lignes par partie : les Blancs (demi-coups pairs) puis les Noirs (demi-coups impairs), empilés."""
    score_blanc = pl.col("Result").replace_strict({"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5})
    return pl.concat([un_cote(games, "White", 0, score_blanc), un_cote(games, "Black", 1, 1 - score_blanc)])


def filtre_joueurs(joueurs):
    """Retire les Elo provisoires (|RatingDiff| > seuil ou manquant) et les pendules anormales
    (berserk = départ à 90 s, temps offert = la pendule remonte de plus que l'incrément)."""
    inc = pl.col("cadence").str.extract(r"\+(\d+)").cast(pl.Int32)
    return joueurs.filter(
        pl.col("rating_diff").abs() <= config.MAX_RATING_DIFF,
        pl.col("clk").list.first().is_between(170, 182),
        pl.col("clk").list.diff().list.max() <= inc,
    )


def main():
    games = pl.read_parquet(config.RAW)
    parties = filtre_parties(games)
    joueurs = filtre_joueurs(une_ligne_par_joueur(parties))
    joueurs.write_parquet(config.JOUEURS)
    print(f"{games.height} parties -> {parties.height} après filtres -> {joueurs.height} lignes joueur-partie")
