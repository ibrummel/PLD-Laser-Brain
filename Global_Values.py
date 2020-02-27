# ToDo: finalize these numbers
# Forcing new commit
SUB_UP = 1
SUB_DOWN = -1
SUB_MANUAL_SPEED = 250
SUB_STEPS_PER_REV = 1000
SUB_BOTTOM = 0
SUB_TOP = 40350
SUB_MM_PER_REV = 2.54 
SUB_STEPS_PER_MM = SUB_STEPS_PER_REV / SUB_MM_PER_REV
#ToDo: measure the minimum target to substrate distance. May want to set a minimum settable height to prevent shooting the substrate holder.
SUB_D0 = 11.6 # mm

TARGET_CW = 1
TARGET_CCW = -1
TARGET_MANUAL_SPEED = 1000
TARGET_STEPS_PER_REV = 6000

AUTO_REPEAT_DELAY = 150
OP_DELAY = 0.01