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

# software emulator...

# data storage
data_stor = {0x0: 0,
             0x1: 0,
            }

# emulating I2C connections
def I2C_write(reg, val):
    data_stor[reg] = val
    return None

def I2C_read(reg):
    return data_stor[reg]


# ===================================
# ============== TEST ===============
# ===================================

from tamalero.ETROC import ETROC

ETROCobj = ETROC(I2C_write, I2C_read)

ETROCobj.test_write(0x0, 1)
testval = ETROCobj.test_read(0x0)
print(testval)
