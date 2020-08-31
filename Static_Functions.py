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

def calc_raster_steps(target_diameter: float, target_utilization=Global.TARGET_UTILIZATION_FRACTION):
    # See calculations in Ian Brummel, Lab Notebook 2, 31 August 2020
    target_diameter = target_diameter * target_utilization
    alpha = np.arccos(1 - (((target_diameter / 2) ** 2)/ (2 * ((Global.CAROUSEL_DIA_MM / 2) ** 2))))
    print(np.rad2deg(alpha))
    raster_steps = alpha * (Global.CAROUSEL_STEPS_PER_REV / (2 * np.pi))

    return int(raster_steps)