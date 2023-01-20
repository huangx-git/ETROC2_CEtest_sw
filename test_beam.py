#!/usr/bin/env python3
import uhal
import argparse
import time
import datetime

IPB_PATH = "ipbusudp-2.0://192.168.0.10:50001"
ADR_TABLE = "../module_test_fw/address_tables/etl_test_fw.xml"

def test_beam(l1a_rate=1, nmin=1):
    """
    Simulates Fermilab's test beam (4s ON, 56s OFF), sending L1A signals at l1a_rate MHz [default = 1] for nmin minutes [default = 1]
    """

    print("Preparing beam...")

    uhal.disableLogging()
    hw = uhal.getDevice("kcu105_daq", IPB_PATH, "file://" + ADR_TABLE)

    trigger_rate = l1a_rate * 1000000 / 25E-9 / (0xffffffff) * 10000

    ON_TIME = 4
    OFF_TIME = 56

    START = time.time()

    for minute in range(nmin):

        print("### Beam ON ###")
        
        start_ON = time.time()

        hw.getNode("SYSTEM.L1A_RATE").write(int(trigger_rate))
        hw.dispatch()

        time.sleep(ON_TIME)
        
        time_diff_ON = time.time() - start_ON

        l1a_rate_cnt_ON = hw.getNode("SYSTEM.L1A_RATE_CNT").read()
        hw.dispatch()

        print("Shutting off beam...") 
        print("\tON time  = {:.2f} s".format(time_diff_ON))
        print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_ON.value()/1000000.0))

        print("### Beam OFF ###")

        start_OFF = time.time()

        hw.getNode("SYSTEM.L1A_RATE").write(0)
        hw.dispatch()

        time.sleep(OFF_TIME)

        time_diff_OFF = time.time() - start_OFF

        l1a_rate_cnt_OFF = hw.getNode("SYSTEM.L1A_RATE_CNT").read()
        hw.dispatch()

        print("{} minutes completed".format(minute+1))
        print("\tOFF time = {:.2f} s".format(time_diff_OFF))
        print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_OFF.value()/1000000.0))

    total_time = round(time.time() - START)
    total_time = str(datetime.timedelta(seconds=total_time))
    print("Test beam simulation completed; it took {}.".format(total_time))

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--l1a_rate', action='store', default=1, type=int, help="L1A rate in MHz. Default is 1 MHz.")
    argParser.add_argument('--time', action='store', default=1, type=int, help='Time in minutes that the beam will run. Default is 1 min.')
    args = argParser.parse_args()

    test_beam(l1a_rate=args.l1a_rate, nmin=args.time)
