# archives : première approche, 1 ligne par joueur

Première version du projet (surtout Yann, avec PL pour le 02). La cible était l'Elo d'un joueur dans une partie
(1 ligne par joueur et par partie).

Le groupe est ensuite passé à l'Elo moyen de la partie (1 ligne par partie) : c'est la solution finale, dans rendu_final/.
Ces fichiers sont gardés parce qu'une bonne partie des idées vient d'eux (filtres, features de pendule et de coups, split par joueur).

- notebooks : 00_extraction -> 01_exploration -> 02_preparation -> 03_features -> 04_modeles
- src_ancien/ : le code de ce pipeline (nettoyage, modèles, figures, extraction, commande python -m elo, chemins)
- figures/ : les graphiques de l'ancien README
- TODO.md : l'ancienne liste de tâches

Ces notebooks sont à lire seulement : leurs résultats sont enregistrés dedans, mais ils ne tournent plus depuis que leur
code a été rangé dans src_ancien/. Seul src/elo/features.py est resté en place, parce que le pipeline final s'en sert.
