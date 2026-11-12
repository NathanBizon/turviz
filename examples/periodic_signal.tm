# Produit une ligne de 1 vers la droite puis revient périodiquement.
# La limite de pas permet d'explorer la forme sans attendre HALT.
SEED,1,R,FORWARD,0,R,FORWARD
FORWARD,1,R,RETURN,0,L,FORWARD
RETURN,1,L,TURN,1,L,RETURN
TURN,0,R,FORWARD,1,R,FORWARD
