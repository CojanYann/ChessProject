"""Features par joueur-partie, calculées avec Polars à partir de la table `blitz_180_joueurs` (notebook 01).
Uniquement les coups du joueur (`san`, `clk`) : les coups adverses renseignent sur le niveau adverse (fuite)."""

import polars as pl

SAN = pl.col("san")
CLK = pl.col("clk")
TEMPS = pl.col("temps")  # ajoutée par `ajoute_temps`


def ajoute_temps(df):
    """`temps` = secondes passées sur chaque coup, alignée sur `san` (1er coup = null : la pendule ne tourne pas)."""
    inc = pl.col("cadence").str.extract(r"\+(\d+)").cast(pl.Int32)
    return df.with_columns(temps=CLK.list.diff() * -1 + inc)


def part(motif):
    """Part des coups du joueur dont le SAN contient `motif` (regex)."""
    return SAN.list.eval(pl.element().str.contains(motif)).list.mean()


PENDULE = {
    "t_ouverture": TEMPS.list.head(10).list.mean(),  # temps moyen par coup, coups 1-10
    "t_milieu": TEMPS.list.slice(10, 15).list.mean(),  # coups 11-25 (null si non atteint)
    "t_finale": TEMPS.list.slice(25).list.mean(),  # coups 26+ (null si non atteint)
    "pct_rapides": TEMPS.list.eval(pl.element() <= 1).list.mean(),
    "pct_longs": TEMPS.list.eval(pl.element() >= 10).list.mean(),
    "t_max": TEMPS.list.max(),
    "coup_t_max": TEMPS.list.arg_max() + 1,
    "cv_temps": pl.when(TEMPS.list.mean() > 0).then(TEMPS.list.std() / TEMPS.list.mean()),
    "pct_zeitnot": CLK.list.eval(pl.element() < 20).list.mean(),
    "temps_restant_fin": CLK.list.last(),
}

ROQUE = SAN.list.eval(pl.element().str.starts_with("O-O"))
COUPS = {
    "pct_captures": part("x"),
    "pct_echecs": part(r"\+"),
    "pct_pions": part("^[a-h]"),
    "pct_cavalier": part("^N"),
    "pct_fou": part("^B"),
    "pct_tour": part("^R"),
    "pct_dame": part("^Q"),
    "pct_roi": part("^K"),
    "petit_roque": SAN.list.eval(pl.element().str.contains(r"^O-O[+#]?$")).list.any(),
    "grand_roque": SAN.list.eval(pl.element().str.starts_with("O-O-O")).list.any(),
    "coup_du_roque": pl.when(ROQUE.list.any()).then(ROQUE.list.arg_max() + 1),
    "dame_precoce": SAN.list.head(5).list.eval(pl.element().str.starts_with("Q")).list.any(),
    "n_promotions": SAN.list.eval(pl.element().str.contains("=")).list.sum(),
}

OUVERTURE = {
    "premier_coup": SAN.list.first(),  # le 1er coup *du joueur* (réponse des Noirs pour les Noirs)
    "eco_lettre": pl.col("eco").str.slice(0, 1),  # A-E : grande famille d'ouverture
}


def ajoute_fin(df):
    """`fin` = comment la partie s'est terminée, du point de vue du joueur.
    Le mat reçu se lit sur le dernier coup adverse (`#`) : on le récupère via `game_id`."""
    mat = SAN.list.last().str.contains("#")
    adv = df.select("game_id", couleur=pl.when(pl.col("couleur") == "White").then(pl.lit("Black")).otherwise(pl.lit("White")), adv_mat=mat)
    s = pl.col("score")
    return (
        df.join(adv, on=["game_id", "couleur"], how="left")
        .with_columns(
            fin=pl.when(s == 0.5).then(pl.lit("nulle"))
            .when(pl.col("termination") == "Time forfeit").then(pl.when(s == 1).then(pl.lit("gagne_au_temps")).otherwise(pl.lit("perd_au_temps")))
            .when(mat).then(pl.lit("mat_donne"))
            .when(pl.col("adv_mat")).then(pl.lit("mat_recu"))
            .when(pl.col("adv_mat").is_null() & (s == 0)).then(pl.lit("inconnu"))  # adversaire filtré : mat ou abandon ?
            .when(s == 1).then(pl.lit("adv_abandonne"))
            .otherwise(pl.lit("a_abandonne"))
        )
        .drop("adv_mat")
    )


def calcule_features(joueurs):
    """Table joueurs -> 1 ligne par joueur-partie avec toutes les features."""
    return (
        ajoute_fin(ajoute_temps(joueurs))
        .select(
            "game_id", "joueur", "elo", "couleur", "cadence", "fin",
            n_coups=SAN.list.len(),
            **PENDULE, **COUPS, **OUVERTURE,
        )
    )
