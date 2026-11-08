"""Génère les figures du compte rendu (COMPTE_RENDU.md) dans figures/.

Deux sources, toutes deux issues d'exécutions réelles :
- les données (Data/blitz_180_raw_full.parquet et Data/blitz_180_parties.parquet) : distribution de l'Elo, entonnoir de
  filtrage, écart d'Elo, seuil RatingDiff, carte des cases de mat ;
- les sorties enregistrées des notebooks de rendu_final/ : MAE par famille de features (tableau du notebook 02),
  graphiques du notebook 03 (MAE par tranche d'Elo, importance des features), courbes du notebook 02.

Lancer depuis la racine du projet, après prepare_raw.py, le nettoyage et les 3 notebooks :
    uv run python rendu_final/figures_compte_rendu.py
"""
import base64
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
sys.path.append(str(RACINE / "src"))
sys.path.append(str(RACINE / "par_personne" / "pl"))  # classes Move / Chessboard de la branche de visualisation
from elo.nettoyage_partie import nettoie  # noqa: E402

DATA = RACINE / "Data"
NOTEBOOKS = RACINE / "rendu_final"
FIGURES = RACINE / "figures"
BLEU, ORANGE, GRIS = "#3B6EA8", "#D9822B", "#8C8C8C"


def sauve(fig, nom):
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(FIGURES / nom, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("figures/" + nom)


# --- Figures calculées sur les données ---------------------------------------------------------------------------
def distribution_elo(raw, parties):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bins = np.arange(400, 3200, 50)
    avant = ((raw["WhiteElo"] + raw["BlackElo"]) / 2).to_numpy()
    ax.hist(avant, bins=bins, density=True, histtype="step", lw=2, color=GRIS, label=f"avant nettoyage ({len(avant):,} parties)".replace(",", " "))
    ax.hist(parties["elo_moyen"].to_numpy(), bins=bins, density=True, alpha=0.6, color=BLEU,
            label=f"dataset final ({parties.height:,} parties)".replace(",", " "))
    ax.set(xlabel="Elo moyen de la partie", ylabel="densité", title="Distribution de la cible avant et après nettoyage")
    ax.legend()
    sauve(fig, "cr_distribution_elo.png")


def entonnoir(raw):
    _, bilan = nettoie(raw)
    etapes = ["départ"] + bilan["étape"].to_list()
    restantes = [raw.height] + bilan["restantes"].to_list()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = np.arange(len(etapes))[::-1]
    ax.barh(y, restantes, color=[GRIS] + [BLEU] * (len(etapes) - 2) + [ORANGE])
    for yi, r in zip(y, restantes):
        ax.text(r + 5_000, yi, f"{r:,}".replace(",", " "), va="center", fontsize=8)
    ax.set_yticks(y, etapes, fontsize=8)
    ax.set(xlabel="parties restantes", title="Entonnoir de nettoyage : 557 237 → 196 124 parties", xlim=(0, 640_000))
    sauve(fig, "cr_entonnoir.png")


def ecart_tournoi(raw):
    games = raw.select(ecart=(pl.col("WhiteElo") - pl.col("BlackElo")).abs(), tournoi=pl.col("Event").str.contains("tournament"))
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bins = np.arange(0, 810, 10)
    for valeur, nom, couleur in [(False, "parties libres", BLEU), (True, "tournois (Arena)", ORANGE)]:
        e = games.filter(pl.col("tournoi") == valeur)["ecart"].clip(upper_bound=800).to_numpy()
        ax.hist(e, bins=bins, density=True, alpha=0.55, color=couleur, label=f"{nom} : médiane {np.median(e):.0f}")
    ax.axvline(200, color="red", ls="--", label="seuil retenu : 200")
    ax.set(yscale="log", xlabel="|Elo Blancs − Elo Noirs| (plafonné à 800)", ylabel="densité (log)",
           title="Écart d'Elo entre les deux joueurs : parties libres et tournois")
    ax.legend()
    sauve(fig, "cr_ecart_elo.png")


def seuil_rating_diff(raw):
    ok = raw.filter((pl.col("WhiteElo") - pl.col("BlackElo")).abs() <= 200)
    cote = lambda c: ok.select(elo=pl.col(f"{c}Elo"), rd=pl.col(f"{c}RatingDiff"))
    par_rd = (
        pl.concat([cote("White"), cote("Black")]).drop_nulls()
        .group_by(rd=pl.col("rd").abs().clip(0, 25)).agg(n=pl.len(), elo=pl.col("elo").mean()).sort("rd")
    )
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.plot(par_rd["rd"], par_rd["elo"], marker="o", color=BLEU)
    ax.axvline(9.5, color="red", ls="--", label="seuil retenu : |RatingDiff| ≤ 9")
    ax.set(xlabel="|RatingDiff| : points gagnés ou perdus après la partie (25 = 25 et plus)", ylabel="Elo moyen des joueurs",
           title="Au-delà de ~10 points de variation, l'Elo retombe vers 1500 : comptes encore provisoires")
    ax.legend()
    sauve(fig, "cr_seuil_rating_diff.png")


def heatmap_mats(parties):
    from chessboard import Chessboard
    from Move import Move

    plateau = Chessboard()
    derniers = parties.filter(pl.col("san").list.last().str.ends_with("#"))["san"].list.last().to_list()
    plateau.count_positions([Move.parse(c) for c in derniers if not c.startswith("O-O")])
    carte = np.zeros((8, 8))
    for (col, rang), n in plateau.board.items():
        carte[int(rang) - 1, ord(col) - ord("a")] = n
    fig, ax = plt.subplots(figsize=(5, 4.4))
    im = ax.imshow(carte, cmap="hot", origin="lower")
    fig.colorbar(im, ax=ax, label="nombre de mats")
    ax.set_xticks(range(8), list("abcdefgh"))
    ax.set_yticks(range(8), range(1, 9))
    ax.set_title(f"Case d'arrivée du coup qui donne mat\n({len(derniers):,} parties finies par mat)".replace(",", " "))
    sauve(fig, "cr_heatmap_mats.png")


# --- Figures tirées des sorties enregistrées des notebooks ---------------------------------------------------------
def sorties(notebook):
    return [c for c in json.loads((NOTEBOOKS / notebook).read_text(encoding="utf-8"))["cells"] if c["cell_type"] == "code"]


def png_de_la_cellule(notebook, debut_code, nom):
    """Recopie l'image PNG produite par la cellule dont le code commence par `debut_code`."""
    for c in sorties(notebook):
        if "".join(c["source"]).startswith(debut_code):
            for o in c.get("outputs", []):
                if "image/png" in o.get("data", {}):
                    FIGURES.mkdir(exist_ok=True)
                    (FIGURES / nom).write_bytes(base64.b64decode(o["data"]["image/png"]))
                    print("figures/" + nom, f"(sortie de {notebook})")
                    return
    raise ValueError(f"aucune image trouvée dans {notebook} pour une cellule commençant par {debut_code!r}")


def tableau_de_la_cellule(notebook, debut_code):
    """Relit un tableau Polars affiché (texte) par la cellule dont le code commence par `debut_code`."""
    for c in sorties(notebook):
        if "".join(c["source"]).startswith(debut_code):
            texte = "".join("".join(o.get("data", {}).get("text/plain", [])) for o in c.get("outputs", []))
            lignes = [l for l in texte.splitlines() if "┆" in l]
            entete, *corps = [[x.strip(" │") for x in l.split("┆")] for l in lignes]
            return [dict(zip(entete, l)) for l in corps if not l[0].startswith("---") and l[0] not in ("str", "f64")]
    raise ValueError(f"aucun tableau trouvé dans {notebook}")


def mae_par_famille():
    lignes = tableau_de_la_cellule("02_features.ipynb", "# 1) Chaque famille seule")
    seules = [l for l in lignes if l["jeu de features"].endswith("seule") or l["jeu de features"].startswith(("baseline", "TOUT"))]
    noms = [l["jeu de features"].replace(" seule", "").replace("TOUT (sélection)", "toutes (sélection)") for l in seules]
    mae = [float(l["MAE"]) for l in seules]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    couleurs = [GRIS if n.startswith("baseline") else ORANGE if n.startswith("toutes") else BLEU for n in noms]
    ax.barh(noms[::-1], mae[::-1], color=couleurs[::-1])
    for i, m in enumerate(mae[::-1]):
        ax.text(m + 2, i, f"{m:.1f}", va="center", fontsize=8)
    ax.set(xlabel="MAE sur le valid (points d'Elo, plus bas = mieux)", xlim=(150, 300),
           title="Ce que chaque famille de features permet d'atteindre (HistGradientBoosting)")
    sauve(fig, "cr_mae_familles.png")


def main():
    raw = pl.read_parquet(DATA / "blitz_180_raw_full.parquet").drop("Movetext", strict=False)
    parties = pl.read_parquet(DATA / "blitz_180_parties.parquet")
    distribution_elo(raw, parties)
    entonnoir(raw)
    ecart_tournoi(raw)
    seuil_rating_diff(raw)
    heatmap_mats(parties)
    mae_par_famille()
    png_de_la_cellule("02_features.ipynb", "def courbes(", "cr_features_par_elo.png")
    png_de_la_cellule("03_modeles.ipynb", "fig, axes = plt.subplots(1, 2", "cr_mae_par_tranche.png")
    png_de_la_cellule("03_modeles.ipynb", "top = importances.head(15)", "cr_importance.png")


if __name__ == "__main__":
    main()
