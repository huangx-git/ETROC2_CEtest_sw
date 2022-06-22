"""
from ETLsystem import initialize

if __name__ == '__main__':

    import argparse

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--force_no_trigger', action='store_true', help="Never initialize the trigger lpGBT.")
    argParser.add_argument('--read_fifo', action='store', default=-1, help='Read 3000 words from link N')
    argParser.add_argument('--load_alignment', action='store', default=None, help='Load predefined alignment, skips the scan.')
    argParser.add_argument('--etroc', action='store', default="ETROC1", help='Load predefined alignment, skips the scan.')

initialize(kcu_adr=args.kcu, force_no_trigger=args.force_no_trigger,
        etroc_ver=args.etroc, load_alignment=args.load_alignment,
        read_fifo=args.read_fifo)
"""

# software emulator

# data storage
data_stor = {0x0: 0, # test register
             0x1: 0, # vth
             0x2: [] # accumulator nums
            }

# emulating I2C connections
def I2C_write(reg, val):
    data_stor[reg] = val
    return None

def I2C_read(reg):
    return data_stor[reg]

# emulating runs


# ===================================
# ============== TEST ===============
# ===================================

from tamalero.ETROC import ETROC

import numpy as np
from matplotlib import pyplot as plt

ETROCobj = ETROC(I2C_write, I2C_read)

print("Test simple read/write...")
ETROCobj.test_write(0x0, 1)
testval = ETROCobj.test_read(0x0)
print(testval)
print("")

N = 3200
vth_min, vth_max = 190, 210
vth_step = 1
testpixel = 10
print("Testing Vth S curve scan for pixel #%d..."%testpixel)

vth_axis = np.arange(vth_min, vth_max, vth_step)
acc_num_axis = np.zeros(vth_axis.size)

for vth in range(vth_min, vth_max, vth_step):
    ETROCobj.set_vth(vth)
    ETROCobj.run(N);
    i = int((vth-vth_min)/vth_step)
    acc_num_axis[i] = ETROCobj.run_results()[testpixel]

plt.title("S curve test") 
plt.xlabel("Vth") 
plt.ylabel("accumulation number") 
plt.plot(vth_axis, acc_num_axis)
plt.show()
