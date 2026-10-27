# TODO

Ordonné du plus simple au plus coûteux. Pour chaque tâche : comparer la MAE (globale et par tranche d'Elo)
au boosting actuel (MAE 241, R² 0,27), avec le même split par joueur (`elo.modeles.split`).

## Court terme

- [ ] Simplifier les features : retirer celles dont l'importance par permutation est < 1 point
      (`petit_roque`, `grand_roque`, `coup_t_max`, `pct_zeitnot`, `couleur`, `pct_fou`, `pct_pions`, `t_milieu`…)
      et vérifier que la MAE ne bouge pas.
- [ ] Vérifier le seuil RatingDiff : MAE des joueurs entre 15 et 20 si on passe le seuil à 20 (cf. notebook 01).
- [ ] Régler le boosting : `max_iter` > 500 (l'arrêt précoce ne s'est presque pas déclenché), `learning_rate`.
      Gain attendu faible.
- [ ] Ajouter au notebook 04 les deux expériences citées dans le README : étirement des prédictions et équilibrage
      des tranches d'Elo (`sample_weight`).
- [ ] Faire importer à `notebooks/01_exploration.ipynb` les fonctions de `src/elo/nettoyage.py` ? (pour l'instant le
      notebook garde le code détaillé, pour l'explication pas à pas : à discuter en groupe).

## Plus de signal (la vraie piste, cf. README « Pourquoi… »)

- [ ] Features d'échiquier (python-chess, étape 4 de la feuille de route), sur les données déjà filtrées :
      pièces laissées en prise, matériel perdu au fil de la partie, menaces ignorées, coups légaux disponibles.
      Utiliser la classe `Move` / `chessboard.py` du groupe si possible.
- [ ] Évaluations `%eval` (9 % des parties) : perte d'évaluation moyenne par coup, nombre de gaffes.
      Décider : modèle à part sur ce sous-ensemble, ou feature manquante pour 91 % des lignes.
      Attention! sous-ensemble biaisé vers les forts (notebook 01).
- [ ] N-grammes de coups : TF-IDF *(Term Frequency × Inverse Document Frequency) Une séquence présente partout reçoit un poids proche de 0 ; une séquence rare, un poids fort. comme en analyse de text*  sur les séquences de coups du joueur (+ `TruncatedSVD` si trop de colonnes), puis Ridge / boosting.
- [ ] Features de pendule plus fines : temps passé sur les coups qui suivent une capture ou un échec adverse
      (réaction aux moments critiques).

## Tâche « niveau d'un joueur » (cf. README, dernière section)

- [ ] Table 1 ligne par (joueur, cadence) avec exactement 10 parties tirées au hasard ; cible = Elo moyen.
- [ ] Features agrégées : moyenne + écart-type des features par partie, diversité des ouvertures, % de fins au temps.
- [ ] Comparer : médiane / moyenne des prédictions « par partie » / modèle sur features agrégées (mêmes joueurs de test).
- [ ] Si prometteur : extraire ~2 jours de données pour atteindre 50 000 joueurs.

## Plus tard

- [ ] Réseau séquentiel sur la suite des coups + temp
- [ ] Étendre à plus de données (plusieurs jours) ou à d'autres cadences, une fois la méthode stabilisée.
