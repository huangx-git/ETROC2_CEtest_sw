#!/usr/bin/env python3

from cocina.PowerSupply import PowerSupply


if __name__ == '__main__':

    ps1 = PowerSupply("Readout", "192.168.2.1")
    ps2 = PowerSupply("Emulator", "192.168.2.2")
    ps3 = PowerSupply("CI", "192.168.2.3")

    print ("\nPS 1 (RBs)")
    ps1.cycle(channel='ch1')
    ps1.cycle(channel='ch2')    
    ps1.monitor()

    print ("\nPS 2 (Emulators)")
    ps2.cycle(channel='ch1')
    ps2.cycle(channel='ch2')
    ps2.monitor()

    print ("\nPS 3 (CI)")
    ps3.cycle(channel='ch1')
    ps3.cycle(channel='ch2')
    ps3.monitor()

