#!/usr/bin/env python3
import uhal
import argparse
from tamalero.utils import get_kcu
from tamalero.ReadoutBoard import ReadoutBoard
from Beam import Beam
from threading import Thread

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--control_hub', action='store_true', default=True, help="Use control hub for communication?")
    argParser.add_argument('--host', action='store', default='localhost', help="Specify host for control hub")
    argParser.add_argument('--l1a_rate', action='store', default=1, type=int, help="L1A rate in MHz")
    argParser.add_argument('--time', action='store', default=1, type=int, help='Time in minutes that the beam will run')
    argParser.add_argument('--verbosity', action='store', default=False)
    argParser.add_argument('--dashboard', action='store', default=True, help='Monitoring dashboard on?')

    args = argParser.parse_args()

    kcu = get_kcu(args.kcu, control_hub=args.control_hub, host=args.host)
    rb  = ReadoutBoard(kcu=kcu)
    beam = Beam(rb)

    Thread(target=beam.generate_beam, args=(args.l1a_rate, args.time), kwargs={'verbose':args.verbosity}).start()
    Thread(target=beam.read_beam, kwargs={'verbose':args.verbosity}).start()
    Thread(target=beam.monitoring_beam, kwargs={'on':args.dashboard}).start()
