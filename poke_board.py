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
    argParser.add_argument('--configuration', action='store', default='modulev0b', choices=['modulev0', 'modulev0b', 'modulev1'], help="Board configuration to be loaded")
    argParser.add_argument('--rbs', action='store', default='0', help="Which RBs to read from")
    argParser.add_argument('--modules', action='store', default='1', help="Modules to read from")
    argParser.add_argument('--etrocs', action='store', default='0', help="ETROCs to read from")
    argParser.add_argument('--temperature', action='store_true', help="Read temperature from ETROC")
    argParser.add_argument('--dark_mode', action='store_true', help="Turn off all LEDs on the RB")
    argParser.add_argument('--light_mode', action='store_true', help="Turn on all LEDs on the RB")
    argParser.add_argument('--bitslip', action='store_true', help="Rerun the bitslip")
    argParser.add_argument('--verbose', action='store_true', help="Rerun the bitslip")
    args = argParser.parse_args()

    rbs = [int(m) for m in args.rbs.split(',')]
    modules = [int(m) for m in args.modules.split(',')]
    etrocs = [int(m) for m in args.etrocs.split(',')]
    temps = []

    # this is the slowest part
    start_time = time.time()
    kcu = get_kcu(args.kcu, control_hub=True, verbose=False, quiet=True)
    kcu_time = time.time()


    for irb in rbs:
        rb = ReadoutBoard(rb=irb, trigger=True, kcu=kcu, config=args.configuration, verbose=False, poke=True)

        if args.temperature:
            for i in modules:
                module = Module(rb, i=i, poke=True)
                for j in etrocs:
                    etroc = module.ETROCs[j]
                    if etroc.is_connected():
                    #if args.temperature:
                        try:
                            temp = etroc.check_temp()
                        except:
                            temp = -1
                        temps.append({'rb': irb, 'mod': etroc.module_id, 'etroc': etroc.chip_no, 'temp': temp})

        if args.dark_mode:
            rb.dark_mode()

        if args.light_mode:
            rb.light_mode()

        if args.bitslip:
            rb.rerun_bitslip()

    if args.temperature:
        print(temps)



    final_time = time.time()

    if args.verbose:
        print("Total time:", final_time-start_time)
        print("- KCU:", kcu_time-start_time)

    #print(etroc.rd_reg('DAC', row=10, col=10))
    #etroc.run_threshold_scan(use=False)
    #print(etroc.rd_reg('DAC', row=10, col=10))
    #etroc.run_threshold_scan(use=True)
    #print(etroc.rd_reg('DAC', row=10, col=10))
