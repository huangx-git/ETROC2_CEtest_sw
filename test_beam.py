#!/usr/bin/env python3
import uhal
import argparse
import time
import datetime
from tamalero.utils import get_kcu


def test_beam(kcu_add, control_hub, host, l1a_rate, nmin):
    """
    Simulates Fermilab's test beam (4s ON, 56s OFF), sending L1A signals at l1a_rate MHz [default = 1] for nmin minutes [default = 1]
    """

    print("Preparing beam...")

    uhal.disableLogging()

    kcu = get_kcu(kcu_add, control_hub=control_hub, host=host)

    trigger_rate = l1a_rate * 1000000 / 25E-9 / (0xffffffff) * 10000

    ON_TIME = 4
    OFF_TIME = 56

    START = time.time()

    for minute in range(nmin):

        print("### Beam ON ###")
        
        start_ON = time.time()

        kcu.write_node("SYSTEM.L1A_RATE", int(trigger_rate))

        time.sleep(ON_TIME)
        
        time_diff_ON = time.time() - start_ON

        l1a_rate_cnt_ON = kcu.read_node("SYSTEM.L1A_RATE_CNT")

        print("Shutting off beam...") 
        print("\tON time  = {:.2f} s".format(time_diff_ON))
        print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_ON.value()/1000000.0))

        print("### Beam OFF ###")

        start_OFF = time.time()

        kcu.write_node("SYSTEM.L1A_RATE", 0)

        time.sleep(OFF_TIME)

        time_diff_OFF = time.time() - start_OFF

        l1a_rate_cnt_OFF = kcu.read_node("SYSTEM.L1A_RATE_CNT")

        print("{} minutes completed".format(minute+1))
        print("\tOFF time = {:.2f} s".format(time_diff_OFF))
        print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_OFF.value()/1000000.0))

    total_time = round(time.time() - START)
    total_time = str(datetime.timedelta(seconds=total_time))
    print("Test beam simulation completed; it took {}.".format(total_time))

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--control_hub', action='store_true', default=False, help="Use control hub for communication?")
    argParser.add_argument('--host', action='store', default='localhost', help="Specify host for control hub")
    argParser.add_argument('--l1a_rate', action='store', default=1, type=int, help="L1A rate in MHz")
    argParser.add_argument('--time', action='store', default=1, type=int, help='Time in minutes that the beam will run')

    args = argParser.parse_args()

    test_beam(args.kcu, args.control_hub, args.host, args.l1a_rate, args.time)
