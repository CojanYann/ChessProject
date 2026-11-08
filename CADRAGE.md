## Cadrage du projet

### Contexte
Les plateformes d'échecs en ligne (Lichess, Chess.com) comme la fédération internationale (FIDE) estiment le niveau d'un joueur uniquement à partir de ses **résultats** (victoire, nulle, défaite), via les systèmes Elo ou Glicko. La qualité du jeu n'entre jamais dans le calcul.

### Problème
Un nouveau joueur n'a donc pas de niveau fiable au départ :
- **Lichess** fait démarrer tout le monde à 1500, avec une note marquée provisoire ;
- **Chess.com** s'appuie sur le niveau déclaré par le joueur à l'inscription ;
- **la FIDE** attend au moins 5 parties officielles avant de publier une première note.

Il faut ensuite de nombreuses parties pour que la note se stabilise. En attendant, les appariements sont déséquilibrés : un débutant affronte des joueurs trop forts, un joueur confirmé écrase des débutants, ce qui dégrade l'expérience des deux.

### Notre proposition
Exploiter une information que ces systèmes ignorent : **la façon de jouer** (coups joués, gestion de la pendule). Nous estimons le niveau d'une partie (l'Elo moyen des deux joueurs) à partir de ces seules données. Le modèle est entraîné sur des joueurs dont l'Elo est stable (les comptes provisoires sont exclus lors du nettoyage, via |RatingDiff| ≤ 9), pour pouvoir ensuite estimer le niveau de joueurs dont l'Elo ne l'est pas encore.

### Métrique
La **MAE** (erreur absolue moyenne, en points d'Elo) : elle se lit directement (« en moyenne, on se trompe de X points »). La RMSE est suivie en parallèle : un écart important entre les deux signale des erreurs ponctuelles très fortes, typiquement sur les niveaux extrêmes.

### Critère de succès
Le modèle doit faire mieux que deux références simples :
1. **prédire 1500 pour tout le monde** (ce que fait Lichess pour un nouveau compte) : MAE ≈ 322 sur le test ;
2. **prédire toujours la médiane** du jeu d'entraînement : MAE ≈ 277 sur le test.

### Limites du cadrage
- Nous prédisons le niveau d'une **partie**, pas d'un joueur seul ; pour un nouveau compte, prédire son niveau individuel serait l'étape suivante.
- Les données couvrent **une seule journée** de Lichess en blitz 3 minutes.

### Perspective
Le même principe (comparer le niveau estimé à l'Elo affiché) pourrait aider à repérer des parties anormales : triche par ordinateur, comptes partagés.

### Sources
- Lichess, systèmes de classement : https://lichess.org/page/rating-systems
- FIDE Rating Regulations (2024) : https://handbook.fide.com/chapter/B022024
- Chess.com, niveaux de départ (forum, à confirmer sur l'aide officielle) : https://chess.com/forum/view/community/how-does-chess-com-decide-initial-ratings
