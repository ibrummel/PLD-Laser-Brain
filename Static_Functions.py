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

def calc_raster_steps(target_diameter: float):
    # See calculations in Ian Brummel, Lab Notebook 1, 27 Feb 2020
    # Note that using diameters works here because we are dividing them out therefore the factors of 2 cancel
    alpha = np.arccos(1 - (target_diameter ** 2) / (Global.CAROUSEL_DIA_INCH ** 2))
    raster_steps = alpha * (Global.SUB_STEPS_PER_REV / (2 * np.pi))

    return int(Global.TARGET_UTILIZATION_FRACTION * raster_steps)