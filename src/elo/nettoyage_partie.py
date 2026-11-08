"""Étape 1 : nettoyage. Version script du notebook `rendu_final/01_nettoyage.ipynb`.

Entrée  : Data/blitz_180_raw_full.parquet (créé par rendu_final/prepare_raw.py), 1 ligne par partie.
Sortie  : Data/blitz_180_parties.parquet, 1 ligne par partie, cible `elo_moyen`, split train / valid / test par joueur.

Le notebook garde l'audit détaillé (sections 3 à 7) qui justifie chaque seuil ; ce module n'applique que les décisions.

Lancer depuis la racine du projet : uv run python -m elo.nettoyage_partie
"""

import chess
import polars as pl

from elo.config import DATA

RAW = DATA / "blitz_180_raw_full.parquet"
SORTIE = DATA / "blitz_180_parties.parquet"

SEED = 42
# Seuils : chacun est justifié dans la section indiquée du notebook 01_nettoyage
MIN_DEMI_COUPS = 20   # section 8 : au moins 10 coups par joueur
ECART_MAX = 200       # section 6.2 : |EloBlancs - EloNoirs| maximal
RD_MAX = 9            # section 6.3 : |RatingDiff| maximal (sinon Elo provisoire)
MAX_PAR_JOUEUR = 20   # section 7 : plafond de parties par joueur
PART_TRAIN, PART_VALID = 0.7, 0.15  # section 9.2 (le reste = test)

GLYPHES = r"[?!]+$"  # annotations `?!`, `??` : présentes seulement dans les parties analysées (fuite)
SYNTAXE_SAN = r"^([PNBRQK]?[a-h]?[1-8]?x?[a-h][1-8](=[NBRQ])?|O-O(-O)?)[+#]?$"


# --- Pendule -----------------------------------------------------------------------------------------------------
def clk_joueur(offset):
    """Pendule d'un joueur (offset 0 = Blancs, 1 = Noirs) : un demi-coup sur deux."""
    return pl.col("clk").list.gather_every(2, offset)


def depart(offset):
    """Temps restant après le premier coup du joueur (180 s attendu ; moins = berserk)."""
    return clk_joueur(offset).list.first()


def remontee(offset):
    """Plus forte remontée de la pendule entre deux coups du joueur (au-delà de l'incrément = temps ajouté)."""
    return clk_joueur(offset).list.diff().list.max()


def pendule_ok(offset):
    return (depart(offset) == 180) & (remontee(offset) <= pl.col("inc"))


# --- Étapes ------------------------------------------------------------------------------------------------------
def prepare_colonnes(raw):
    """Colonnes de travail (aucune ligne retirée) : identifiant, coups sans annotations, pendule en secondes."""
    coup = pl.element().struct
    t = coup.field("clk").str.to_time("%H:%M:%S")
    en_secondes = t.dt.hour().cast(pl.Int32) * 3600 + t.dt.minute().cast(pl.Int32) * 60 + t.dt.second().cast(pl.Int32)
    # En-têtes rares : absents si aucune partie lue ne les contient
    manquantes = [c for c in ("WhiteTitle", "BlackTitle") if c not in raw.columns]
    raw = raw.with_columns(pl.lit(None, dtype=pl.String).alias(c) for c in manquantes)
    return raw.with_columns(
        game_id=pl.col("Site").str.extract(r"lichess\.org/(\w+)"),
        san=pl.col("moves").list.eval(coup.field("san").str.replace(GLYPHES, "")),
        clk=pl.col("moves").list.eval(en_secondes),
        ecart=(pl.col("WhiteElo") - pl.col("BlackElo")).abs(),
        inc=pl.col("TimeControl").str.extract(r"\+(\d+)").cast(pl.Int32),  # incrément : 0 ou 2 s
    ).drop("moves")


def filtres():
    """Les filtres de partie, dans l'ordre. Une condition `null` retire la partie."""
    est_bot = (pl.col("WhiteTitle") == "BOT").fill_null(False) | (pl.col("BlackTitle") == "BOT").fill_null(False)
    return {
        "BOT": ~est_bot,
        "Abandoned / Rules infraction": ~pl.col("Termination").is_in(["Abandoned", "Rules infraction"]),
        f"moins de {MIN_DEMI_COUPS} demi-coups": pl.col("n_moves") >= MIN_DEMI_COUPS,
        "pendule manquante": ~pl.col("clk").list.eval(pl.element().is_null()).list.any(),
        "pendule anormale (berserk, temps ajouté)": pendule_ok(0) & pendule_ok(1),
        f"écart d'Elo > {ECART_MAX}": pl.col("ecart") <= ECART_MAX,
        f"Elo provisoire (|RatingDiff| > {RD_MAX})": (pl.col("WhiteRatingDiff").abs() <= RD_MAX)
        & (pl.col("BlackRatingDiff").abs() <= RD_MAX),
    }


def applique_filtres(games):
    """Applique les filtres puis retire les doublons exacts. Renvoie la table et le bilan étape par étape."""
    clean, bilan = games, []
    for nom, garder in filtres().items():
        avant = clean.height
        clean = clean.filter(garder)
        bilan.append({"étape": nom, "retirées": avant - clean.height, "restantes": clean.height})

    avant = clean.height
    clean = clean.unique("san", keep="first", maintain_order=True)  # même suite de coups = même partie
    bilan.append({"étape": "doublon exact de la partie", "retirées": avant - clean.height, "restantes": clean.height})
    return clean, bilan


def plafonne_par_joueur(clean):
    """Garde au plus MAX_PAR_JOUEUR parties par joueur, tirées au hasard (un joueur très actif ne domine pas)."""
    cote = lambda c: clean.select("game_id", joueur=pl.col(c), alea=pl.int_range(pl.len()).shuffle(seed=SEED))
    rangs = (
        pl.concat([cote("White"), cote("Black")])
        .with_columns(rang=pl.col("alea").rank("ordinal").over("joueur"))
        .group_by("game_id")
        .agg(rang_max=pl.col("rang").max())
    )
    return clean.join(rangs.filter(pl.col("rang_max") <= MAX_PAR_JOUEUR), on="game_id")


def split_par_joueur(clean):
    """Tire un split (train / valid / test) par joueur ; garde les parties dont les deux joueurs sont dans le même."""
    joueurs = pl.concat([clean["White"], clean["Black"]]).unique().sort()
    fold = (
        pl.DataFrame({"joueur": joueurs})
        .with_columns(u=pl.int_range(pl.len()).shuffle(seed=SEED) / pl.len())
        .with_columns(
            split=pl.when(pl.col("u") < PART_TRAIN).then(pl.lit("train"))
            .when(pl.col("u") < PART_TRAIN + PART_VALID).then(pl.lit("valid"))
            .otherwise(pl.lit("test"))
        )
        .select("joueur", "split")
    )
    clean = (
        clean.join(fold.rename({"joueur": "White", "split": "split_blanc"}), on="White")
        .join(fold.rename({"joueur": "Black", "split": "split_noir"}), on="Black")
    )
    return clean.filter(pl.col("split_blanc") == pl.col("split_noir")).rename({"split_blanc": "split"}).drop("split_noir")


def table_finale(clean):
    """Les colonnes du dataset final. Pseudos et split servent à grouper, jamais comme features."""
    return clean.select(
        "game_id",
        "split",
        blanc=pl.col("White"),
        noir=pl.col("Black"),
        elo_moyen=(pl.col("WhiteElo") + pl.col("BlackElo")) / 2,
        cadence=pl.col("TimeControl"),
        eco=pl.col("ECO"),
        n_moves=pl.col("n_moves"),
        san=pl.col("san"),
        clk=pl.col("clk"),
    ).sort("game_id")


# --- Contrôles ---------------------------------------------------------------------------------------------------
def nb_parties_illegales(parties, n=20_000):
    """Rejoue n parties tirées au hasard avec python-chess et compte celles qui contiennent un coup illégal."""
    illegales = 0
    for coups in parties.sample(min(n, parties.height), seed=SEED)["san"].to_list():
        plateau = chess.Board()
        try:
            for c in coups:
                plateau.push_san(c)
        except ValueError:
            illegales += 1
    return illegales


def controles(parties):
    """Vérifications automatiques du dataset final : {nom: True/False}."""
    inc = pl.col("cadence").str.extract(r"\+(\d+)").cast(pl.Int32)
    joueurs_par_split = (
        pl.concat([parties.select("split", joueur="blanc"), parties.select("split", joueur="noir")])
        .unique()
        .group_by("joueur")
        .len()
    )
    return {
        "game_id unique": parties["game_id"].n_unique() == parties.height,
        "aucune valeur manquante": parties.null_count().to_numpy().sum() == 0,
        "elo_moyen entre 400 et 3200": parties["elo_moyen"].min() >= 400 and parties["elo_moyen"].max() <= 3200,
        "len(san) == len(clk) == n_moves": parties.filter(
            (pl.col("san").list.len() != pl.col("n_moves")) | (pl.col("clk").list.len() != pl.col("n_moves"))
        ).height == 0,
        f"n_moves >= {MIN_DEMI_COUPS}": parties["n_moves"].min() >= MIN_DEMI_COUPS,
        "aucune annotation ?! dans les coups": parties.select(
            pl.col("san").list.eval(pl.element().str.contains(r"[?!]")).list.any().any()
        ).item() is False,
        "syntaxe SAN valide": parties.select("san").explode("san").filter(~pl.col("san").str.contains(SYNTAXE_SAN)).height == 0,
        "départ pendule = 180 s (2 joueurs)": parties.filter((depart(0) != 180) | (depart(1) != 180)).height == 0,
        "pendule sans remontée > incrément": parties.filter((remontee(0) > inc) | (remontee(1) > inc)).height == 0,
        "aucun joueur dans 2 splits": joueurs_par_split.filter(pl.col("len") > 1).height == 0,
        f"aucun joueur > {MAX_PAR_JOUEUR} parties": pl.concat([parties["blanc"], parties["noir"]]).value_counts()["count"].max()
        <= MAX_PAR_JOUEUR,
        "parties légales (20 000 rejouées)": nb_parties_illegales(parties) == 0,
    }


# --- Pipeline ----------------------------------------------------------------------------------------------------
def nettoie(raw):
    """Table brute -> (dataset final, bilan des parties retirées à chaque étape)."""
    clean, bilan = applique_filtres(prepare_colonnes(raw))

    avant = clean.height
    clean = plafonne_par_joueur(clean)
    bilan.append({"étape": f"plafond {MAX_PAR_JOUEUR} parties / joueur", "retirées": avant - clean.height, "restantes": clean.height})

    avant = clean.height
    clean = split_par_joueur(clean)
    bilan.append({"étape": "parties croisées entre splits", "retirées": avant - clean.height, "restantes": clean.height})

    return table_finale(clean), pl.DataFrame(bilan)


def main():
    if not RAW.exists():
        raise FileNotFoundError(f"{RAW} introuvable : lancer d'abord `uv run python rendu_final/prepare_raw.py`.")
    raw = pl.read_parquet(RAW).drop("Movetext", strict=False)
    print(f"départ : {raw.height} parties")

    parties, bilan = nettoie(raw)
    with pl.Config(tbl_rows=20, fmt_str_lengths=50):
        print(bilan)

    resultats = controles(parties)
    for nom, ok in resultats.items():
        print("OK   " if ok else "ECHEC", nom)
    assert all(resultats.values()), "au moins un contrôle a échoué : le dataset n'est pas écrit"

    parties.write_parquet(SORTIE)
    print(SORTIE, "->", parties.height, "parties")
    print(parties.group_by("split").len().sort("split"))


if __name__ == "__main__":
    main()
