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
SUB_DMAX = 114.088 # mm

CAROUSEL_CW = 1
CAROUSEL_CCW = -1
CAROUSEL_MANUAL_SPEED = 1000
CAROUSEL_STEPS_PER_REV = 6000
CAROUSEL_DIA_INCH = 3.75 # inch, measured
CAROUSEL_DIA_MM = CAROUSEL_DIA_INCH * 25.4  # mm, calculated

AUTO_REPEAT_DELAY = 150
OP_DELAY = 0.01

TARGET_UTILIZATION_FRACTION = 0.9