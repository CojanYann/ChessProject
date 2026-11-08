"""Features par partie (Blancs + Noirs) pour la table `blitz_180_parties` (rendu_final/01_nettoyage.ipynb).

Tout est calculé uniquement à partir des coups (`san`) et de la pendule (`clk`) : aucune information de résultat ou d'Elo.
- pendule / coups : on réutilise `elo.features` (dicts d'expressions par joueur), appliqué aux Blancs puis aux Noirs ;
- ouverture : profondeur de théorie, calculée sur les parties d'entraînement uniquement ;
- matériel : rejeu des parties avec python-chess (valeur des pièces 1-3-3-5-9).
"""

from concurrent.futures import ProcessPoolExecutor

import chess
import polars as pl

from elo.features import COUPS, PENDULE, TEMPS, CLK, SAN, ajoute_temps

# --- Pendule : features en plus de `elo.features.PENDULE` (par joueur) -----------------------------------------
PENDULE_PLUS = {
    "clk_coup_10": CLK.list.get(9, null_on_oob=True),  # temps restant après son 10e / 20e / 30e coup
    "clk_coup_20": CLK.list.get(19, null_on_oob=True),
    "clk_coup_30": CLK.list.get(29, null_on_oob=True),
    "t_median": TEMPS.list.median(),
    "part_t_ouverture": pl.when(TEMPS.list.sum() > 0).then(TEMPS.list.head(10).list.sum() / TEMPS.list.sum()),
}


def features_cote(parties, offset):
    """Features d'un joueur (offset 0 = Blancs, 1 = Noirs) : 1 ligne par partie, même ordre que `parties`."""
    cote = parties.select(
        "game_id",
        "cadence",
        san=pl.col("san").list.gather_every(2, offset),
        clk=pl.col("clk").list.gather_every(2, offset),
    )
    return ajoute_temps(cote).select(
        "game_id", **PENDULE, **COUPS, **PENDULE_PLUS
    ).with_columns(pl.col(pl.Boolean).cast(pl.Float64))


def features_pendule_coups(parties):
    """Pour chaque feature `f` : `f_b` (Blancs), `f_n` (Noirs) et `f` = moyenne des deux (les null sont ignorés)."""
    b, n = features_cote(parties, 0), features_cote(parties, 1)
    noms = [c for c in b.columns if c != "game_id"]
    both = pl.concat(
        [b.rename({c: c + "_b" for c in noms}), n.drop("game_id").rename({c: c + "_n" for c in noms})],
        how="horizontal",
    )
    return both.with_columns(
        **{c: pl.mean_horizontal(pl.col(f"{c}_b").cast(pl.Float64), pl.col(f"{c}_n").cast(pl.Float64)) for c in noms}
    )


# --- Ouverture ----------------------------------------------------------------------------------------------------
def profondeur_theorie(parties, seuil=20, max_plies=40):
    """Nombre de demi-coups pendant lesquels la partie suit une suite *déjà jouée* au moins `seuil` fois ailleurs
    dans les parties d'entraînement (proxy de la connaissance théorique : les forts restent plus longtemps dans la théorie).
    Les compteurs viennent du train seul ; pour une partie du train on retire la partie elle-même."""
    est_train = (parties["split"] == "train").cast(pl.Int32)
    profondeur = pl.Series("profondeur_theorie", [0] * parties.height, dtype=pl.Int32)
    for d in range(1, max_plies + 1):
        cle = parties.select(cle=pl.col("san").list.head(d).list.join(" "))["cle"]
        compte = (
            pl.DataFrame({"cle": cle, "train": est_train})
            .with_columns(n=pl.col("train").sum().over("cle"))  # nb de parties du train avec la même suite
        )["n"]
        profondeur = profondeur + ((compte - est_train >= seuil) & (parties["n_moves"] >= d)).cast(pl.Int32)
    return profondeur


# --- Matériel (python-chess) --------------------------------------------------------------------------------------
VALEURS = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def _materiel_cote(plateau, couleur):
    return sum(v * chess.popcount(plateau.pieces_mask(pt, couleur)) for pt, v in VALEURS.items())


def materiel(coups):
    """Rejoue une partie : renvoie (balance, total) après chaque demi-coup.
    balance = matériel Blancs - Noirs ; total = Blancs + Noirs (78 au départ)."""
    plateau, blancs, noirs = chess.Board(), 39, 39
    balance, total = [], []
    for san in coups:
        coup = plateau.parse_san(san)
        change = plateau.is_capture(coup) or coup.promotion is not None
        plateau.push(coup)
        if change:  # le matériel ne bouge que sur une prise ou une promotion
            blancs, noirs = _materiel_cote(plateau, chess.WHITE), _materiel_cote(plateau, chess.BLACK)
        balance.append(blancs - noirs)
        total.append(blancs + noirs)
    return balance, total


def _materiel_lot(lot):
    return [materiel(coups) for coups in lot]


def calcule_materiel(parties, taille_lot=2000):
    """Colonnes `mat` (balance) et `mat_tot` (total) pour toutes les parties, calcul en parallèle (~1 min)."""
    coups = parties["san"].to_list()
    lots = [coups[i : i + taille_lot] for i in range(0, len(coups), taille_lot)]
    with ProcessPoolExecutor() as pool:
        resultats = [r for lot in pool.map(_materiel_lot, lots) for r in lot]
    return pl.DataFrame(
        {
            "game_id": parties["game_id"],
            "mat": [r[0] for r in resultats],
            "mat_tot": [r[1] for r in resultats],
        },
        schema_overrides={"mat": pl.List(pl.Int16), "mat_tot": pl.List(pl.Int16)},
    )


MAT, TOT = pl.col("mat"), pl.col("mat_tot")
ABS_MAT = MAT.list.eval(pl.element().abs())
# prise « gratuite » : une pièce (>= 3) change de camp et n'est pas reprise au coup suivant
GRATUITE = (pl.element().diff().abs() >= 3) & (pl.element().diff(2).shift(-1).abs() >= 3)

MATERIEL = {
    "mat_abs_moy": ABS_MAT.list.mean(),  # déséquilibre moyen du matériel
    "mat_abs_max": ABS_MAT.list.max(),
    "mat_abs_fin": MAT.list.last().abs(),
    "mat_tot_20": TOT.list.get(19, null_on_oob=True),  # matériel restant au demi-coup 20 / 40 / 60
    "mat_tot_40": TOT.list.get(39, null_on_oob=True),
    "mat_tot_60": TOT.list.get(59, null_on_oob=True),
    "mat_tot_fin": TOT.list.last(),
    "ply_finale": pl.when(TOT.list.eval(pl.element() <= 40).list.any()).then(TOT.list.eval(pl.element() <= 40).list.arg_max() + 1),
    "n_gratuites": MAT.list.eval(GRATUITE).list.sum(),
}

# --- Autres features de partie ------------------------------------------------------------------------------------
PARTIE = {
    "fini_par_mat": SAN.list.last().str.ends_with("#").cast(pl.Float64),
    "premiere_prise": pl.when(SAN.list.eval(pl.element().str.contains("x")).list.any()).then(
        SAN.list.eval(pl.element().str.contains("x")).list.arg_max() + 1
    ),
    "ouv_blanc": SAN.list.get(0),
    "ouv_noir": SAN.list.get(1),
    "eco_lettre": pl.col("eco").str.slice(0, 1),
}
