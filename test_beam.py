#!/usr/bin/env python3
import uhal
import argparse
from tamalero.utils import get_kcu
from Beam import Beam
from threading import Thread

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--control_hub', action='store_true', default=False, help="Use control hub for communication?")
    argParser.add_argument('--host', action='store', default='localhost', help="Specify host for control hub")
    argParser.add_argument('--l1a_rate', action='store', default=1, type=int, help="L1A rate in MHz")
    argParser.add_argument('--time', action='store', default=1, type=int, help='Time in minutes that the beam will run')

    args = argParser.parse_args()

    kcu = get_kcu(args.kcu, control_hub=args.control_hub, host=args.host)
    beam = Beam(kcu)

    Thread(target=beam.generate_beam, args=(args.l1a_rate, args.time)).start()
    Thread(target=beam.read_beam).start()
