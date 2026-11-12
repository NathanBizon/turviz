# Produces a line of 1s to the right, then returns periodically.
# The step limit lets you explore the shape without waiting for HALT.
SEED,1,R,FORWARD,0,R,FORWARD
FORWARD,1,R,RETURN,0,L,FORWARD
RETURN,1,L,TURN,1,L,RETURN
TURN,0,R,FORWARD,1,R,FORWARD
