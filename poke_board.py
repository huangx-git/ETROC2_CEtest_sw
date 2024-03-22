#!/usr/bin/env python3

import time
import copy
from emoji import emojize

from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import get_kcu, load_yaml
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame
from tamalero.Module import Module

if __name__ == '__main__':


    import argparse
    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default='192.168.0.10', help="IP Address of KCU105 board")
    argParser.add_argument('--configuration', action='store', default='modulev0b', choices=['modulev0', 'modulev0b'], help="Board configuration to be loaded")
    argParser.add_argument('--rb', action='store', default=0, type=int, choices=[0,1,2,3,4], help="Board configuration to be loaded")
    argParser.add_argument('--temperature', action='store_true', help="Read temperature from ETROC")
    argParser.add_argument('--dark_mode', action='store_true', help="Turn off all LEDs on the RB")
    argParser.add_argument('--light_mode', action='store_true', help="Turn on all LEDs on the RB")
    argParser.add_argument('--bitslip', action='store_true', help="Rerun the bitslip")
    args = argParser.parse_args()

    kcu = get_kcu(args.kcu, control_hub=True, verbose=False, quiet=True)

    rb = ReadoutBoard(rb=int(args.rb), trigger=True, kcu=kcu, config=args.configuration, verbose=False, poke=True)

    module = Module(rb, i=1, poke=True)
    etroc = module.ETROCs[0]

    if args.temperature:
        try:
            temp = etroc.check_temp()
        except:
            temp = -1
        print(temp)

    if args.dark_mode:
        rb.dark_mode()

    if args.light_mode:
        rb.light_mode()

    if args.bitslip:
        rb.rerun_bitslip()

    #print(etroc.rd_reg('DAC', row=10, col=10))
    #etroc.run_threshold_scan(use=False)
    #print(etroc.rd_reg('DAC', row=10, col=10))
    #etroc.run_threshold_scan(use=True)
    #print(etroc.rd_reg('DAC', row=10, col=10))
