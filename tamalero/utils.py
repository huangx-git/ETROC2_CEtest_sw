import math


def get_temp(v_out, v_ref, r_ref, t_1, r_1, b, celcius=True):
    """
    Calculate the temperature of a thermistor, given the voltage measured on it.

    Arguments:
    v_out (float) -- voltage measured on the thermistor
    v_ref (float) -- reference voltage
    r_ref (float) -- volatge divider resistor
    t_1 (float) -- reference temperature of thermistor
    r_1 (float) -- resistance of NTC at reference temperature
    b (float) -- B coefficient, with B = (ln(r_1)-ln(r_t)) / (1/t_1 - 1/t_out)

    Keyword arguments:
    celcius (bool) -- give and return the temperature in degree celcius. Kelvin scale used otherwise.
    """

    delta_t = 273.15 if celcius else 0
    r_t = r_ref / (v_ref/v_out - 1)
    t_2 = b/((b/(t_1+delta_t)) - math.log(r_1) + math.log(r_t))
    return t_2-delta_t


if __name__ == '__main__':
    print ("Temperature example:")
    print (get_temp(0.8159, 1.5, 10000, 25, 10000, 3900))
