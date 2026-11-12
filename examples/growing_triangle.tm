# Builds three cells set to 1, returns left, then halts.
# Useful for observing the head and tape width.
START,1,R,SECOND,1,R,SECOND
SECOND,1,R,THIRD,1,R,THIRD
THIRD,1,L,RETURN,1,L,RETURN
RETURN,0,L,RETURN,HALT
