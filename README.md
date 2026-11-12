## TurViz

TurViz lit et visualise l'histoire de la bande d'une machine de Turing.

### Installation et lancement

Le projet utilise [uv](https://docs.astral.sh/uv/).

```shell
uv sync
uv run turviz
```

### Machines d'exemple

Le dossier `examples/` contient plusieurs machines prêtes à ouvrir :

- `busy_beaver_3.tm` : une machine compacte avec une trace riche et un arrêt ;
- `growing_triangle.tm` : construction d'une zone de cellules à `1` ;
- `two_state_cycle.tm` : cycle volontairement non terminant pour tester l'analyse ;
- `periodic_signal.tm` : motif périodique à explorer avec la limite de pas.

### Format `.tm`

Une ligne commence par le nom de l'état, puis décrit la branche pour le symbole
`0` et celle pour le symbole `1`. Une branche normale contient trois champs :
`écriture, déplacement (L/R), nouvel état`. Une branche d'arrêt est simplement
`HALT` et ne contient aucun champ supplémentaire.

Les fichiers existants restent valides : sans directive, le premier état
déclaré est l'état initial. Pour rendre ce choix explicite, un fichier peut
ajouter avant ses transitions :

```text
@version 1
@initial START
```

`@version 1` active la version actuelle du format et `@initial` permet de
choisir n'importe quel état déclaré comme point de départ. Chaque directive
est optionnelle, ne peut apparaître qu'une fois et les directives inconnues
sont signalées avec leur ligne.

```text
A,1,R,B,0,L,B
B,HALT,1,R,A
```

Les espaces autour des virgules, les lignes vides et les commentaires commençant
par `#` sont acceptés. Le premier état déclaré est l'état initial. La bande est
initialisée avec des `0`, la tête commence en position `0`, et l'exécution
s'arrête sur `HALT` ou lorsque la limite de pas est atteinte. La visualisation
utilise le noir pour `0`, le blanc pour `1` et le gris pour la position de la
tête lorsque cette option est active dans le moteur de rendu. Dans l'interface,
la tête est colorée avec une teinte HSV différente pour chaque état, ce qui
permet de suivre visuellement les changements d'état au fil des étapes.
Le panneau inférieur de l'éditeur liste également chaque état, sa couleur et
ses transitions pour les symboles `0` et `1`. Après une exécution, l'état final
est marqué comme actif.
Un onglet `Graphe` dans ce même panneau affiche en complément les états sous
forme de nœuds colorés et les transitions orientées, avec les boucles sur
elles-mêmes. Les transitions `0` et `1` entre deux mêmes états sont courbées
dans des directions opposées et leurs étiquettes disposent d'un fond opaque
pour rester lisibles lorsque le graphe est dense.
La tête est dessinée avec 50 % de transparence : la teinte de l'état reste
visible tout en laissant distinguer la valeur `0` ou `1` de la cellule située
dessous.
Après une exécution, le curseur `Étape` et les boutons précédent/suivant
permettent d'inspecter la trace progressivement. Le tableau et le graphe se
recentrent alors sur l'état courant, tandis que la barre d'état indique la
position de la tête et le nombre de cellules valant `1`.
Le bouton `Lire` lance aussi une lecture automatique de la trace ; la durée
entre deux étapes est réglable en millisecondes et la lecture s'arrête
automatiquement à la fin.
Pour créer rapidement une machine, le bouton `Ajouter un état` ouvre un
formulaire guidé pour les deux branches, avec choix de `HALT`, écriture,
déplacement et état cible. `Ctrl+Entrée` exécute la machine et `Ctrl+S`
l'enregistre.
TurViz détecte également les cycles : si une configuration complète (état,
position de tête et contenu de la bande) se répète, l'exécution s'arrête et
indique le début ainsi que la période du cycle. Cela permet d'identifier
rapidement les machines qui ne termineront pas et d'explorer leurs motifs
périodiques.
Le panneau `Insights` résume la portion de trace actuellement affichée :
largeur de la zone explorée, largeur maximale de cette zone, maximum de cellules
à `1` et nombre final de cellules à `1`. Ces valeurs évoluent pendant la
lecture pas à pas.
Le rendu des grandes traces est borné à une fenêtre autour de l'étape courante
et aux dernières lignes de la trace : le fond de la bande est peint en une
seule opération, puis seuls les `1` et les positions de tête sont dessinés.
Les zéros implicites ne déclenchent donc pas un dessin individuel, ce qui
évite les allocations d'images démesurées.