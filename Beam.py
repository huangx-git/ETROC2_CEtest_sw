#!/usr/bin/env python3
import uhal
import time
import struct
import datetime

class Beam():
    def __init__(self, kcu):
        try:
            self.kcu = kcu
        except:
            print("Unable to connect to KCU.")
        self.ON = 4
        self.OFF = 56

    def generate_beam(self, l1a_rate, nmin):
        """
        Simulates Fermilab's test beam (4s ON, 56s OFF), sending L1A signals at l1a_rate MHz [default = 1] for nmin minutes [default = 1]
        """

        self.SIM = True

        print("Preparing beam...")

        uhal.disableLogging()

        self.l1a_rate = l1a_rate
        self.nmin = nmin

        self.trigger_rate = self.l1a_rate * 1000000 / 25E-9 / (0xffffffff) * 10000

        ON_TIME = self.ON
        OFF_TIME = self.OFF

        START = time.time()

        for minute in range(self.nmin):

            print("### Beam ON ###")

            self.kcu.write_node("SYSTEM.L1A_RATE", int(self.trigger_rate))

            time.sleep(1)

            start_ON = time.time()

            time.sleep(ON_TIME)
            
            time_diff_ON = time.time() - start_ON

            l1a_rate_cnt_ON = self.kcu.read_node("SYSTEM.L1A_RATE_CNT")

            print("Shutting off beam...") 
            print("\tON time  = {:.2f} s".format(time_diff_ON))
            print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_ON.value()/1000000.0))

            print("### Beam OFF ###")

            self.kcu.write_node("SYSTEM.L1A_RATE", 0)

            time.sleep(1)

            start_OFF = time.time()

            time.sleep(OFF_TIME)

            time_diff_OFF = time.time() - start_OFF

            l1a_rate_cnt_OFF = self.kcu.read_node("SYSTEM.L1A_RATE_CNT")

            print("{} minutes completed".format(minute+1))
            print("\tOFF time = {:.2f} s".format(time_diff_OFF))
            print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_OFF.value()/1000000.0))

        total_time = round(time.time() - START)
        total_time = str(datetime.timedelta(seconds=total_time-2))
        print("Test beam simulation completed; it took {}.".format(total_time))
        self.SIM = False

    # Pseudocode:
    #   Code should run non-stop while test_beam.py is running / beam is being simulated
    #   let data = []
    #   while True:
    #       if L1A rate is 0 Hz:
    #           with open file as f:
    #               write data to file
    #       read FIFO data
    #       if FIFO data is not empty:
    #           add FIFO data to data

    def read_beam(self, block=255, verbose=False):

        data = []

        if verbose: start = time.time()
        while self.SIM == True:
            l1a_rate_cnt = self.kcu.read_node("SYSTEM.L1A_RATE_CNT")
            if l1a_rate_cnt.value() == 0:
                with open("output/read_beam.dat", mode="wb") as f:
                    f.write(struct.pack('<{}I'.format(len(data)), *data))
                    if verbose:
                        time_diff = round(time.time() - start)
                        time_diff = str(datetime.timedelta(seconds=time_diff))
                        print(f"Writing after {time_diff}")
            
            try:
                # Check FIFO occupancy
                occupancy = self.kcu.read_node("READOUT_BOARD_0.RX_FIFO_OCCUPANCY")
                num_blocks_to_read = occupancy.value() // block

                # Read data from FIFO
                if (num_blocks_to_read):
                    reads = num_blocks_to_read * [self.kcu.hw.getNode("DAQ_RB0").readBlock(block)]
                    self.kcu.dispatch()
                    for read in reads:
                        data += read.value()
            except uhal._core.exception:
                print("uhal UDP error in daq")
