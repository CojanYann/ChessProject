"""Étape 5 : graphes PNG du README (dans `figures/`), à partir des fichiers produits par les étapes précédentes."""

import matplotlib

matplotlib.use("Agg")  # pas de fenêtre : on enregistre seulement les images
import matplotlib.pyplot as plt
import polars as pl

from elo import config
from elo.nettoyage import filtre_parties, une_ligne_par_joueur

MODELES = ["mediane", "lineaire", "boosting"]


def sauve(fig, nom):
    fig.tight_layout()
    fig.savefig(config.FIGURES / f"{nom}.png", dpi=110)
    plt.close(fig)
    print("  figures/" + nom + ".png")


def par_tranche(df, pas, *aggs, n_min=300):
    """Agrégations par tranche d'Elo réel (tranches trop petites retirées)."""
    return (
        df.with_columns(tranche=pl.col("elo") // pas * pas + pas // 2)
        .group_by("tranche")
        .agg(n=pl.len(), *aggs)
        .filter(pl.col("n") >= n_min)
        .sort("tranche")
    )


def seuil_rating_diff():
    """Elo moyen selon |RatingDiff|, avant filtre des joueurs : le plateau justifie le seuil."""
    joueurs = une_ligne_par_joueur(filtre_parties(pl.read_parquet(config.RAW)))
    t = (
        joueurs.drop_nulls("rating_diff")
        .group_by(d=pl.col("rating_diff").abs().clip(upper_bound=40))
        .agg(elo=pl.col("elo").mean())
        .filter(pl.col("d") >= 3)
        .sort("d")
    )
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(t["d"], t["elo"], marker=".")
    ax.axvline(config.MAX_RATING_DIFF, color="red", ls="--", label=f"seuil retenu : {config.MAX_RATING_DIFF}")
    ax.set(xlabel="|RatingDiff| sur la partie (40 = 40 et plus)", ylabel="Elo moyen", title="Elo moyen selon la variation d'Elo")
    ax.grid(alpha=0.3)
    ax.legend()
    sauve(fig, "seuil_rating_diff")


def distribution_elo(joueurs):
    t = (
        joueurs.group_by("cadence", elo=pl.col("elo") // 25 * 25)
        .agg(n=pl.len())
        .with_columns(pct=pl.col("n") / pl.col("n").sum().over("cadence") * 100)
        .sort("elo")
    )
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for cadence, d in t.group_by("cadence", maintain_order=True):
        ax.plot(d["elo"], d["pct"], label=cadence[0])
    ax.set(xlabel="Elo", ylabel="% des joueurs-parties", title="Distribution de l'Elo (Blitz 3 min)")
    ax.grid(alpha=0.3)
    ax.legend()
    sauve(fig, "distribution_elo")


def features_par_elo(feats):
    cols = ["t_ouverture", "pct_rapides", "cv_temps", "coup_t_max", "n_coups", "pct_captures", "petit_roque", "dame_precoce"]
    t = par_tranche(feats, 100, *[pl.col(c).cast(pl.Float64).mean() for c in cols], n_min=1000)
    fig, axes = plt.subplots(2, 4, figsize=(14, 5.5), sharex=True)
    for ax, c in zip(axes.flat, cols):
        ax.plot(t["tranche"], t[c], marker=".")
        ax.set_title(c, fontsize=10)
        ax.grid(alpha=0.3)
    fig.supxlabel("Elo")
    fig.suptitle("Moyenne de quelques features par tranche d'Elo")
    sauve(fig, "features_par_elo")


def fins_et_ouvertures(feats):
    mode = pl.col("fin").str.replace_all(r"^(mat_.*)$", "mat").str.replace_all(r".*abandonne$", "abandon")
    mode = mode.str.replace_all(r".*au_temps$", "temps").replace("inconnu", None)
    fins = par_tranche(feats.with_columns(mode=mode).drop_nulls("mode"), 200, *[
        (pl.col("mode") == m).mean().alias(m) * 100 for m in ["mat", "abandon", "temps", "nulle"]
    ], n_min=1000)
    blancs = feats.filter(pl.col("couleur") == "White")
    coups = ["e4", "d4", "Nf3", "c4"]
    ouv = par_tranche(blancs, 200, *[(pl.col("premier_coup") == c).mean().alias(c) * 100 for c in coups], n_min=1000)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    for m in ["mat", "abandon", "temps", "nulle"]:
        ax1.plot(fins["tranche"], fins[m], marker=".", label=m)
    ax1.set(xlabel="Elo", ylabel="% des parties", title="Comment finissent les parties")
    for c in coups:
        ax2.plot(ouv["tranche"], ouv[c], marker=".", label=c)
    ax2.set(xlabel="Elo", ylabel="% des parties (Blancs)", title="Premier coup des Blancs")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.legend()
    sauve(fig, "fins_et_ouvertures")


def regression_vers_la_moyenne(preds):
    """Gauche : prédiction moyenne par Elo réel. Droite : Elo réel moyen par prédiction (calibration)."""
    t = par_tranche(preds, 100, *[pl.col(m).mean() for m in MODELES])
    calib = (
        preds.group_by(p=pl.col("boosting") // 50 * 50 + 25)
        .agg(n=pl.len(), elo=pl.col("elo").mean())
        .filter(pl.col("n") >= 300)
        .sort("p")
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))
    ax1.plot(t["tranche"], t["tranche"], "k--", label="parfait")
    for m in MODELES:
        ax1.plot(t["tranche"], t[m], marker=".", label=m)
    ax1.set(xlabel="Elo réel", ylabel="Elo prédit moyen", title="Par Elo réel : les prédictions sont écrasées vers 1700")
    ax2.plot(calib["p"], calib["p"], "k--", label="parfait")
    ax2.plot(calib["p"], calib["elo"], marker=".", color="C2", label="boosting")
    ax2.set(xlabel="Elo prédit", ylabel="Elo réel moyen", title="Par prédiction : le modèle est bien calibré")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.legend()
    sauve(fig, "regression_vers_la_moyenne")


def mae_par_elo(preds):
    t = par_tranche(preds, 100, *[(pl.col(m) - pl.col("elo")).abs().mean() for m in MODELES])
    fig, ax = plt.subplots(figsize=(8, 3.5))
    for m in MODELES:
        ax.plot(t["tranche"], t[m], marker=".", label=m)
    ax.set(xlabel="Elo réel", ylabel="MAE", title="Erreur selon l'Elo")
    ax.grid(alpha=0.3)
    ax.legend()
    sauve(fig, "mae_par_elo")


def importances(imp):
    t = imp.head(15).sort("hausse_MAE")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(t["feature"], t["hausse_MAE"])
    ax.set(xlabel="hausse de la MAE quand on mélange la feature", title="Importance par permutation (boosting, top 15)")
    ax.grid(alpha=0.3, axis="x")
    sauve(fig, "importances")


def erreur_et_information(preds):
    """Gauche : MAE selon la longueur de la partie. Droite : MAE en moyennant k parties d'un même joueur."""
    erreur = (pl.col("boosting") - pl.col("elo")).abs()
    longueur = (
        preds.group_by(n_coups=pl.col("n_coups").clip(upper_bound=60) // 5 * 5)
        .agg(boosting=erreur.mean(), mediane=(pl.col("mediane") - pl.col("elo")).abs().mean())
        .sort("n_coups")
    )
    multi = (
        preds.sample(fraction=1, shuffle=True, seed=config.SEED)
        .with_columns(rang=pl.int_range(pl.len()).over("joueur"), n_parties=pl.len().over("joueur"))
        .filter(pl.col("n_parties") >= 20)
    )
    ks = [1, 2, 3, 5, 10, 20]
    mae_k = [
        multi.filter(pl.col("rang") < k).group_by("joueur").agg(p=pl.col("boosting").mean(), elo=pl.col("elo").mean())
        .select((pl.col("p") - pl.col("elo")).abs().mean()).item()
        for k in ks
    ]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    for m in ["boosting", "mediane"]:
        ax1.plot(longueur["n_coups"], longueur[m], marker=".", label=m)
    ax1.set(xlabel="coups du joueur (60 = 60 et plus)", ylabel="MAE", title="Erreur selon la longueur de la partie")
    ax1.legend()
    ax2.plot(ks, mae_k, marker="o")
    ax2.set(xscale="log", xticks=ks, xticklabels=ks, xlabel="parties moyennées par joueur", ylabel="MAE",
            title="Moyenner plusieurs parties : plateau vers 207")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
    sauve(fig, "erreur_et_information")


def main():
    config.FIGURES.mkdir(exist_ok=True)
    feats, preds = pl.read_parquet(config.FEATURES), pl.read_parquet(config.PREDICTIONS)
    seuil_rating_diff()
    distribution_elo(pl.read_parquet(config.JOUEURS, columns=["elo", "cadence"]))
    features_par_elo(feats)
    fins_et_ouvertures(feats)
    regression_vers_la_moyenne(preds)
    mae_par_elo(preds)
    importances(pl.read_parquet(config.IMPORTANCES))
    erreur_et_information(preds)
