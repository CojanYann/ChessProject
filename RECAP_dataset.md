# Récapitulatif : exploration, audit et construction du dataset « Elo moyen »

**Objectif** : construire un dataset fiable et prêt pour le ML afin de prédire `elo_moyen = (EloBlancs + EloNoirs) / 2`
à partir des coups (SAN) et de la pendule, sur les parties Blitz 3 min de Lichess (septembre 2026).

Tout le détail (code, tableaux, graphiques) est dans [notebooks/03_nettoyage_elo_moyen.ipynb](notebooks/03_nettoyage_elo_moyen.ipynb).
Ce fichier en résume la démarche et les résultats.

---

## 1. Ce qui a été produit

| Fichier | Statut | Rôle |
|---|---|---|
| [notebooks/03_nettoyage_elo_moyen.ipynb](notebooks/03_nettoyage_elo_moyen.ipynb) | nouveau | audit + nettoyage + split + contrôles + fiche du dataset |
| `Data/blitz_180_raw_full.parquet` | généré (non versionné) | 2M premières parties du PGN, filtrées 180+0 / 180+2 : **557 237 parties** |
| `Data/blitz_180_parties.parquet` | généré (non versionné) | **dataset final : 196 124 parties**, 1 ligne par partie |
| [CLAUDE.md](CLAUDE.md) | modifié | ajout du notebook 03 et de ses décisions dans les notes du projet |
| `RECAP_dataset.md` | nouveau | ce fichier |

Les fichiers de `Data/` sont ignorés par git. Le fichier `Data/blitz_180_raw.parquet` existant (2 883 parties seulement, très
inférieur aux 557k décrits dans les notes) n'a **pas** été modifié ; le notebook 03 régénère son propre cache depuis le PGN
s'il est absent (~1 min).

---

## 2. Démarche

1. **Lecture du dépôt** : notebooks 01 (1 ligne/joueur, exploration) et 02 (choix de cadence), `src/utils/pgn.py`, notes du projet
   (Polars uniquement, pas de Stockfish, notebooks simples, split par joueur, anti-fuite).
2. **Première version** du notebook 03 : nettoyage simple (mêmes filtres que le notebook 01, 1 ligne/partie). Jugée insuffisante.
3. **Exploration approfondie des 557k parties** avant d'écrire le notebook final : chaque anomalie a été mesurée, et le notebook
   n'applique de seuil que lorsque les données le justifient.
4. **Notebook final** : sections 3 à 7 = audit (aucune ligne retirée), section 8 = application de tous les filtres,
   section 9 = plafond par joueur et split, section 10 = contrôles automatiques, section 11 = sauvegarde et fiche du dataset.

---

## 3. Résultats de l'audit

| Sujet | Constat mesuré | Décision |
|---|---|---|
| **Structure** | `Date`, `Round`, `UTCDate` constantes. `RatingDiff` manquant pour 1 514 parties (abandons). | colonnes inutiles non conservées |
| **Couverture** | les 2M parties lues couvrent **00h-16h UTC** du 1er septembre seulement ; Elo moyen plat selon l'heure (~1680). 8,6 % de tournois Arena. | un seul jour : limite documentée |
| **Parsing des coups** | 0 partie où `n_moves` ≠ nombre de numéros de coups du texte brut. | parsing fiable |
| **Annotations `?!`, `??`** | **53 061** parties en contiennent, et *toutes* sont des parties analysées (`%eval`) ; l'inverse n'arrive jamais. L'analyse existe surtout pour les joueurs forts : indice caché sur la cible. | glyphes retirés des SAN (`Qxf7?!` → `Qxf7`) |
| **`%eval`** | ~8-10 % des parties jusqu'à 2000 Elo, puis ~20 % à 2200 et ~50 % à 2600. | non utilisé, colonne non conservée |
| **Légalité** | 0 partie illégale sur 20 000 rejouées avec `python-chess` ; 131 157 mats, 0 résultat incohérent. | données de coups fiables |
| **Pendule** | aucune pendule négative ; départ à 90 s (berserk) pour 26 % des parties de tournoi contre 0,04 % des parties libres ; 1 513 parties avec temps ajouté. | retirer berserk / temps ajouté / départ ≠ 180 s |
| **Cohérence des Elo** | `Elo(suivante) = Elo(précédente) + RatingDiff(précédente)` vérifié à **99,4 %** sur 951 464 paires de parties consécutives. | Elo fiables |
| **Écart d'Elo entre joueurs** | libre : médiane 28, p99 184 ; tournoi : médiane 156, p99 884. | garder **écart ≤ 200** (≈ 96 % des parties ; erreur de la moyenne ≤ 100, soit ~1/3 de la MAE baseline) |
| **Elo provisoires** | à écart ≤ 200, l'Elo moyen tombe vers 1500 à partir de \|RatingDiff\| ≈ 10 (compte neuf). | garder **\|RatingDiff\| ≤ 9** pour les deux joueurs |
| **Concentration** | 160 772 joueurs, médiane 4 parties, max 228 ; les joueurs à ≥ 20 parties fournissent 33 % des lignes. 1 943 paires s'affrontent ≥ 5 fois (record 124). | plafond de **20 parties par joueur** |
| **Doublons** | quelques dizaines de parties longues dont toute la suite de coups est identique (scripts). Les ouvertures de théorie identiques sur 20 demi-coups sont légitimes. | garder la 1re occurrence des doublons exacts |
| **Fuite** | l'Elo adverse prédit quasi parfaitement l'Elo du joueur (corr. 0,96) ; `RatingDiff`, résultat et `%eval` renseignent sur le niveau sans venir des coups. | aucune de ces colonnes dans le dataset |

---

## 4. Pipeline appliqué (section 8-9 du notebook)

| Étape | Parties retirées | Restantes |
|---|---:|---:|
| Départ | | 557 237 |
| BOT | 1 610 | 555 627 |
| Abandoned / Rules infraction | 1 576 | 554 051 |
| < 20 demi-coups | 18 165 | 535 886 |
| Pendule manquante | 0 | 535 886 |
| Pendule anormale (berserk, temps ajouté) | 13 498 | 522 388 |
| Écart d'Elo > 200 | 15 352 | 507 036 |
| Elo provisoire (\|RatingDiff\| > 9) | 53 181 | 453 855 |
| Doublon exact de la partie | 53 | 453 802 |
| Plafond 20 parties / joueur | 86 872 | 366 930 |
| Parties « croisées » entre folds (split par joueur, 70/15/15) | 170 806 | **196 124** |

**Split par joueur** : chaque joueur reçoit un fold (aléatoire, `SEED = 42`) ; seules les parties dont les deux joueurs sont dans le
même fold sont gardées. Un même joueur garde quasiment le même Elo toute la journée et un style reconnaissable : un split par
partie ferait fuir l'information entre train et test. Un premier essai en 80/10/10 ne donnait que ~3 700 parties en test ;
70/15/15 en donne ~8 300.

---

## 5. Dataset final `blitz_180_parties.parquet`

| Colonne | Type | Rôle |
|---|---|---|
| `game_id` | str | clé |
| `blanc`, `noir` | str | pseudos : pour grouper/splitter, **jamais en feature** |
| `split` | str | `train` / `valid` / `test` (par joueur) |
| `elo_moyen` | float | **cible** |
| `cadence` | str | `180+0` ou `180+2` |
| `eco` | str | ouverture (déduite des coups) |
| `n_moves` | int | nombre de demi-coups |
| `san` | list[str] | coups, Blancs aux indices pairs, sans annotations |
| `clk` | list[int] | pendule restante (secondes) après chaque demi-coup, même indexation |

| Split | Parties | Part | Elo moyen | MAE baseline (médiane du train = 1691,5) |
|---|---:|---:|---:|---:|
| train | 179 356 | 91,5 % | 1678 | 281,2 |
| valid | 8 428 | 4,3 % | 1675 | 271,9 |
| test | 8 340 | 4,3 % | 1688 | 276,6 |

Avant nettoyage : Elo moyen 1680, écart-type 353 ; après : 1679 et 348. La population garde donc la même forme.

### Contrôles automatiques (tous OK, `assert` dans le notebook)
`game_id` unique · aucune valeur manquante · `elo_moyen` entre 400 et 3200 · `len(san) == len(clk) == n_moves` ·
`n_moves ≥ 20` · aucune annotation `?!` · syntaxe SAN valide · départ pendule = 180 s pour les deux joueurs ·
aucune remontée de pendule > incrément · aucun joueur dans deux splits · ≤ 20 parties par joueur ·
20 000 parties rejouées légalement.

---

## 6. Limites à garder en tête

- **Un seul jour** (1er sept. 2026, 00h-16h UTC) et **une seule famille de cadence** (blitz 3 min) : la généralisation à d'autres
  jours ou cadences n'est pas démontrée. Pour plus de diversité, lire d'autres jours du PGN (~27 s par million de parties).
- **Population filtrée** : plus de comptes neufs (Elo provisoires), plus de gros écarts d'Elo ni de tournois ; le modèle sera
  moins fiable sur ces profils.
- **Extrêmes rares** (< 1000, > 2400) : un modèle aura tendance à les ramener vers le centre.
- **Valid et test petits** (~8 000 parties) à cause du split par joueur ; une validation croisée par groupes de joueurs sur le
  train peut compléter.
- Les seuils (écart 200, \|RatingDiff\| 9, plafond 20, min 20 demi-coups) sont des **choix justifiés par les données mais
  ajustables** : ce sont des constantes en tête du notebook.

## 7. Étapes suivantes (feuille de route du projet)

1. Features sur `san` et `clk` pour chaque couleur (`gather_every(2, 0)` / `gather_every(2, 1)`) : temps sur les premiers coups,
   % de coups rapides, captures, roque, etc.
2. Régression linéaire, à comparer à la baseline (MAE ≈ 280).
3. Features d'échiquier (`python-chess`), puis n-grammes TF-IDF, puis modèle séquentiel.
