from math import trunc
import Global_Values as Global
import numpy as np

def truncate(number, decimals=0):
    # Deprecated with external triggering, everything should be calculated on pulse counts now and times should be
    # rounded for display purposes
    if decimals < 0:
        raise ValueError('Cannot truncate to negative decimals ({})'.format(decimals))
    elif decimals == 0:
        return trunc(number)
    else:
        factor = float(10 ** decimals)
        return trunc(number * factor) / factor

def calc_raster_steps(target_diameter: float, target_utilization=1.0):
    # See calculations in Ian Brummel, Lab Notebook 2, 16 June 2020
    target_diameter = target_diameter * target_utilization
    alpha = np.arccos((((target_diameter / 2) ** 2)/ (2 * ((Global.CAROUSEL_DIA_MM / 2) ** 2))) - 1)
    raster_steps = alpha * (Global.SUB_STEPS_PER_REV / (2 * np.pi))

    return int(Global.TARGET_UTILIZATION_FRACTION * raster_steps)