import math
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


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


def read_mapping(f_in, selection='adc', flavor='small'):
    flavors = {'small':0, 'medium':1, 'large': 2}
    i_flavor = flavors[flavor]
    with open(f_in) as f:
        mapping = load(f, Loader=Loader)[selection]
    return {v:mapping[v] for v in mapping.keys() if flavors[mapping[v]['flavor']] <= flavors[flavor]}


if __name__ == '__main__':
    print ("Temperature example:")
    print (get_temp(0.8159, 1.5, 10000, 25, 10000, 3900))
