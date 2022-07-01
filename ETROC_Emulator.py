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

maxpixel = 256

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

# initiate pixel array with some noisy baseline
def init_bl():
    print("initiating some fake properties")
    default_mean  = 198
    default_stdev =   1
    global bl_means
    global bl_stdevs
    bl_means  = [np.random.normal( default_mean,  1) for x in range(maxpixel)]
    bl_stdevs = [np.random.normal(default_stdev, .1) for x in range(maxpixel)]


# ETROC data format

class ETROCdata():
    def __init__(self, BCID="0x000"):
        self.BCID = BCID
        self.hitdata = []

    def add_hit(self,row,col,TOA,TOT,CAL,P):
        self.hitdata.append(
                format(row, '04b') + format(col,'04b')
              + format(TOA,'010b') + format(TOT,'09b') + format(CAL, '010b')
              + format(  P,  '1b'))

    def fullevent(self):
        Nhit    = len(self.hitdata)
        header  = "00"+format(0x3555555,'026b')+format(BCID,'012b')
        hitdata = "".join(self.hitdata)
        trailer = "10"+format(0x5555555,'028b')+format(Nhit,'09b')+format(P,'1b')
        return header + hitdata + trailer


# run simulated hits

def runpixel(N, pixel):
    acc_num = 0
    vth = I2C_read(0x1)

    for i in range(N):
        # produce random hit
        val = np.random.normal(bl_means[pixel], bl_stdevs[pixel])
        if val > vth :
            acc_num += 1

    return acc_num

def run(N):
    rundata = [0 for x in range(maxpixel)]
    for pixel in range(maxpixel):
        rundata[pixel] = runpixel(N, pixel)
    I2C_write(0x2, rundata)
    return rundata
