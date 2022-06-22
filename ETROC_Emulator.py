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
import numpy as np

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

def runpixel(N):
    acc_num = 0
    vth = I2C_read(0x1)
    for i in range(N):
        val = np.random.normal(198, 0.5)
        if val > vth :
            acc_num += 1
    return acc_num

def run(N):
    maxpixel = 16
    alldata = [0 for x in range(maxpixel)]
    for pixel in range(maxpixel):
        alldata[pixel] = runpixel(N)
    I2C_write(0x2, alldata)
