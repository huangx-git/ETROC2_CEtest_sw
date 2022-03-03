import math
import numpy as np
from time import sleep
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

def dump_alignment_to_file(rb, f_out):
    res = rb.dump_uplink_alignment()
    with open(f_out, 'w') as f:
        dump(res, f, Dumper=Dumper)

def load_alignment_from_file(f_in):
    with open(f_in, 'r') as f:
        res = load(f, Loader=Loader)
    return res

def prbs_phase_scan(lpgbt, f_out='phase_scan.txt'):
    with open(f_out, "w") as f:
        for phase in range(0x0, 0x1ff, 1):
            phase_ns = (50.0*(phase&0xf) + 800.0*(phase>>4))/1000
            lpgbt.set_ps0_phase(phase)
            lpgbt.reset_pattern_checkers()
            sleep(0.5)
            #read_pattern_checkers()
            prbs_errs = lpgbt.read_pattern_checkers(quiet=True)[0]
            s = ("{} "*(len(prbs_errs)+1)).format(*([phase_ns]+prbs_errs))
            f.write("%s\n" % s)
            print (s)


def plot_phase_scan(f_in, channel):
    import matplotlib.pyplot as plt
    data = np.loadtxt(f_in)
    plt.yscale("log")
    plt.plot(data[:,0], data[:,channel])
    plt.show()


def header():
    from tamalero.colors import magenta
    print(magenta("\n\n\
    ████████╗ █████╗ ███╗   ███╗ █████╗ ██╗     ███████╗███████╗\n\
    ╚══██╔══╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝██╔════╝\n\
       ██║   ███████║██╔████╔██║███████║██║     █████╗  ███████╗\n\
       ██║   ██╔══██║██║╚██╔╝██║██╔══██║██║     ██╔══╝  ╚════██║\n\
       ██║   ██║  ██║██║ ╚═╝ ██║██║  ██║███████╗███████╗███████║\n\
       ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝\n\n\
    "))


def make_version_header(res):
    from tamalero.colors import blue
    print ("\n\n ### Testing ETL Readout Board: ###")
    print (blue("- Version: %s.%s"%(res["rb_ver_major"], res["rb_ver_minor"])))
    print (blue("- Flavor: %s"%res["rb_flavor"]))
    print (blue("- Serial number: %s"%res["serial_number"]))
    print (blue("- lpGBT version: %s"%res["lpgbt_ver"]))
    print (blue("- lpGBT serial number: %s"%res['lpgbt_serial']))
    print (blue("- Trigger lpGBT mounted: %s"%res['trigger']))
    print ("\n")


def chunk(in_list, n):
    return [in_list[i * n:(i + 1) * n] for i in range((len(in_list) + n - 1) // n )] 


if __name__ == '__main__':
    print ("Temperature example:")
    print (get_temp(0.8159, 1.5, 10000, 25, 10000, 3900))
