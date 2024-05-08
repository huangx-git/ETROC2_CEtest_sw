#!/usr/bin/env python3

from cocina.PowerSupply import PowerSupply
import argparse

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--verbose', action='store_true', default=False, help="Verbose PSU monitor")
    argParser.add_argument('--power_down', action='store_true', default=False, help="Just power down")
    argParser.add_argument('--ip', action='store', default="192.168.2.3", help="IP address of PSU to power cycle")
    argParser.add_argument('--ch', action='store', default="ch1,ch2", help="Channels of PSU to power cycle")
    args = argParser.parse_args()

    assert args.ch in "ch1,ch2", "Only channel 1 and channel 2 are available."

    if args.ip == "192.168.2.1":
        name = "Readout"
    elif args.ip == "192.168.2.2":
        name = "Emulator"
    elif args.ip == "192.168.2.3":
        name = "CI"
    else:
        name = "Unknown"

    psu = PowerSupply(name, args.ip)
   
    print (f"PS -- {name}")
    channels = [ch for ch in args.ch.split(',')]

    for ch in channels:
        if args.power_down:
            psu.power_down(channel=ch)
        else:
            psu.cycle(channel=ch)
    if args.verbose:
        psu.monitor()

