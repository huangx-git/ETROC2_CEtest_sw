#!/usr/bin/env python3
import uhal
import argparse
from tamalero.utils import get_kcu
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.Beam import Beam
from threading import Thread

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--control_hub', action='store_true', help="Use control hub for communication?")
    argParser.add_argument('--host', action='store', default='localhost', help="Specify host for control hub")
    argParser.add_argument('--l1a_rate', action='store', default=1000, type=float, help="L1A rate in  kHz")
    argParser.add_argument('--time', action='store', default=1, type=int, help='Time in minutes that the beam will run')
    argParser.add_argument('--verbosity', action='store', default=False)
    argParser.add_argument('--dashboard', action='store', default=True, help='Monitoring dashboard on?')

    args = argParser.parse_args()

    kcu  = get_kcu(args.kcu, control_hub=args.control_hub, host=args.host)
    rb   = ReadoutBoard(kcu=kcu)
    beam = Beam(rb)

    print(f"----------------------------------")
    print(f"       test_beam Parameters       ")
    print(f" Dashboard   : {args.dashboard}   ")
    print(f" Control hub : {args.control_hub} ")
    print(f" Host        : {args.host}        ")
    print(f" L1A rate    : {args.l1a_rate}    ")
    print(f" # Spills    : {args.time}        ")
    print(f"----------------------------------")

    Thread(target=beam.generate_beam, args=(args.l1a_rate, args.time), kwargs={'verbose':args.verbosity}).start()
    Thread(target=beam.read_fifo, kwargs={'verbose':args.verbosity}).start()
    if args.dashboard == True:
        Thread(target=beam.monitor).start()
