# archives : première approche, 1 ligne par joueur

Ces notebooks sont la première version du projet (surtout Yann, avec PL pour le 02). La cible était l'Elo d'un joueur
dans une partie (1 ligne par joueur et par partie).

Le groupe est ensuite passé à l'Elo moyen de la partie (1 ligne par partie), voir CADRAGE.md et les notebooks
du dossier notebooks/. Ces notebooks sont gardés ici parce qu'une bonne partie des idées vient d'eux
(filtres, features de pendule et de coups, split par joueur).

Ordre de lecture : 00_extraction -> 01_exploration -> 02_preparation -> 03_features -> 04_modeles.
Ils tournent toujours depuis ce dossier (chemins ../Data/...). Le code qu'ils utilisent est dans src/elo/,
dont features.py est toujours utilisé par le nouveau pipeline.
