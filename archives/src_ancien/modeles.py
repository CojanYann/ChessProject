"""Étape 4 : split par joueur, baseline, régression linéaire et gradient boosting (détails : notebook 04)."""

import numpy as np
import polars as pl
import polars.selectors as cs
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from elo import config

CAT = ["couleur", "cadence", "fin", "premier_coup", "eco_lettre"]
ID = ["game_id", "joueur", "elo"]


def charge():
    """Features prêtes pour sklearn : booléens -> 0/1, `fin = inconnu` (artefact du nettoyage) -> `a_abandonne`."""
    return pl.read_parquet(config.FEATURES).with_columns(
        cs.boolean().cast(pl.Float64),
        pl.col("fin").replace("inconnu", "a_abandonne"),
    )


def colonnes_num(feats):
    return [c for c in feats.columns if c not in CAT + ID]


def split(feats):
    """80/20 par joueur : toutes les parties d'un joueur sont du même côté (pas de fuite par le style du joueur)."""
    decoupe = GroupShuffleSplit(n_splits=1, test_size=config.TEST_SIZE, random_state=config.SEED)
    train_idx, test_idx = next(decoupe.split(feats, groups=feats["joueur"]))
    return feats[train_idx], feats[test_idx]


def lineaire(num):
    """Imputation médiane + indicateur de manquant, standardisation, one-hot.
    `pct_pions` retirée : les pct_* somment à ~1 (colinéarité -> coefficients arbitraires)."""
    num = [c for c in num if c != "pct_pions"]
    return make_pipeline(
        ColumnTransformer([
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), num),
            ("cat", OneHotEncoder(min_frequency=0.01, handle_unknown="infrequent_if_exist"), CAT),
        ]),
        LinearRegression(),
    )


def boosting(num):
    """Gère seul les manquants et les catégorielles ; arrêt précoce sur 10 % du train."""
    return make_pipeline(
        ColumnTransformer([
            ("cat", OrdinalEncoder(min_frequency=0.01, handle_unknown="use_encoded_value", unknown_value=-1), CAT),
            ("num", "passthrough", num),
        ]),
        HistGradientBoostingRegressor(categorical_features=list(range(len(CAT))), max_iter=500, random_state=config.SEED),
    )


def scores(y, pred):
    return {
        "MAE": round(mean_absolute_error(y, pred), 1),
        "RMSE": round(root_mean_squared_error(y, pred), 1),
        "R2": round(r2_score(y, pred), 3),
    }


def importance_permutation(modele, X, y, n=50_000, repetitions=3):
    """Hausse de la MAE quand on mélange une colonne (= casse son lien avec l'Elo), sur n lignes."""
    idx = np.random.default_rng(config.SEED).choice(len(y), n, replace=False)
    X, y = X[idx], y[idx]
    ref = mean_absolute_error(y, modele.predict(X))
    hausse = [
        np.mean([mean_absolute_error(y, modele.predict(X.with_columns(pl.col(c).shuffle(seed=s)))) for s in range(repetitions)]) - ref
        for c in X.columns
    ]
    return pl.DataFrame({"feature": X.columns, "hausse_MAE": hausse}).sort("hausse_MAE", descending=True)


def main():
    feats = charge()
    num = colonnes_num(feats)
    train, test = split(feats)
    X_train, y_train = train.select(CAT + num), train["elo"].to_numpy()
    X_test, y_test = test.select(CAT + num), test["elo"].to_numpy()

    modeles = {"lineaire": lineaire(num), "boosting": boosting(num)}
    preds = {"mediane": np.full(len(y_test), np.median(y_train))}
    for nom, modele in modeles.items():
        preds[nom] = modele.fit(X_train, y_train).predict(X_test)

    print(pl.DataFrame([{"modele": nom, **scores(y_test, p)} for nom, p in preds.items()]))
    test.select("joueur", "elo", "n_coups").with_columns(**{nom: pl.Series(p) for nom, p in preds.items()}).write_parquet(
        config.PREDICTIONS
    )
    importances = importance_permutation(modeles["boosting"], X_test, y_test)
    importances.write_parquet(config.IMPORTANCES)
    print(importances.head(10))
