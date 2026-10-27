"""Point d'entrée du pipeline :  uv run python -m elo <étape> [<étape> ...]   (ou `tout`)."""

import argparse
import time

from elo import extraction, features, figures, modeles, nettoyage

ETAPES = {
    "extraction": extraction.main,  # PGN (téléchargé si absent, ~28 Go) -> blitz_180_raw.parquet      1-4 min
    "nettoyage": nettoyage.main,  # -> blitz_180_joueurs.parquet                                      ~15 s
    "features": features.main,  # -> blitz_180_features.parquet                                       ~5 s
    "modeles": modeles.main,  # scores + predictions_test.parquet + importances.parquet             ~2 min
    "figures": figures.main,  # -> figures/*.png                                                     ~15 s
}

parser = argparse.ArgumentParser(prog="python -m elo", description="Pipeline : prédire l'Elo à partir des coups.")
parser.add_argument("etapes", nargs="+", choices=[*ETAPES, "tout"], help="étape(s) à lancer, dans l'ordre")
args = parser.parse_args()

for nom in list(ETAPES) if "tout" in args.etapes else args.etapes:
    t0 = time.time()
    print(f"== {nom}")
    ETAPES[nom]()
    print(f"   ({time.time() - t0:.0f} s)")
