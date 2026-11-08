## Cadrage du projet

### Contexte
Les plateformes d'échecs en ligne (Lichess, Chess.com) comme la fédération internationale (FIDE) estiment le niveau d'un joueur uniquement à partir de ses **résultats** (victoire, nulle, défaite), via les systèmes Elo ou Glicko. La qualité du jeu n'entre jamais dans le calcul.

Un nouveau joueur n'a donc pas de niveau fiable au départ :
- **Lichess** fait démarrer tout le monde à 1500, avec une note marquée provisoire ;
- **Chess.com** s'appuie sur le niveau déclaré par le joueur à l'inscription ;
- **la FIDE** attend au moins 5 parties officielles avant de publier une première note.

### Problème
L'Elo affiché ne reflète pas toujours le vrai niveau d'un joueur, dans deux situations :
- **les nouveaux comptes** : ils démarrent tous au même niveau, et il faut de nombreuses parties pour que leur note se stabilise ;
- **les smurfs** : des joueurs confirmés qui jouent sur un compte au classement plus bas que leur vrai niveau.

Dans les deux cas, les appariements sont déséquilibrés : des joueurs plus faibles affrontent des adversaires bien trop forts pour eux, ce qui dégrade leur expérience.

### Notre proposition
Exploiter l'information que les systèmes de classement ignorent : **la façon de jouer** (coups joués, gestion de la pendule). Nous estimons l'Elo d'un joueur à partir de **ses seuls coups et de sa pendule** dans une partie, sans utiliser ni l'Elo de l'adversaire, ni ses coups, ni le résultat de la partie.

Comparer ce niveau estimé à l'Elo affiché permet de signaler les joueurs dont la note semble décalée : un écart important et répété sur plusieurs parties peut indiquer un compte encore mal classé ou un smurf.

Le modèle est entraîné sur des joueurs dont l'Elo est stable : les comptes provisoires sont exclus lors du nettoyage, à partir de la variation de note après la partie (`RatingDiff`).

### Métrique
La **MAE** (erreur absolue moyenne, en points d'Elo) : elle se lit directement (« en moyenne, on se trompe de X points »). La RMSE est suivie en parallèle : un écart important entre les deux signale des erreurs ponctuelles très fortes, typiquement sur les niveaux extrêmes.

### Critère de succès
Le modèle doit faire mieux que deux références simples, sur des joueurs absents de l'entraînement :
1. **prédire 1500 pour tout le monde** (le point de départ de Lichess pour un nouveau compte) ;
2. **prédire toujours la médiane** du jeu d'entraînement.

### Limites du cadrage
- Il n'existe pas d'étiquette « smurf » dans les données : la détection est une application du modèle, pas un résultat que nous pouvons mesurer directement. La performance est évaluée sur la prédiction de l'Elo.
- Une seule partie est un indice bruité du niveau : une détection fiable suppose d'agréger plusieurs parties d'un même joueur.
- Les données couvrent **une seule journée** de Lichess en blitz 3 minutes.

### Perspective
Le même principe (comparer le niveau estimé à l'Elo affiché) pourrait aider à repérer d'autres parties anormales, comme la triche par ordinateur ou les comptes partagés.

### Sources
- Lichess, systèmes de classement : https://lichess.org/page/rating-systems
- FIDE Rating Regulations (2024) : https://handbook.fide.com/chapter/B022024
- Chess.com, niveaux de départ (forum, à confirmer sur l'aide officielle) : https://chess.com/forum/view/community/how-does-chess-com-decide-initial-ratings
