#!/usr/bin/env python3
import struct
import numpy as np
import aiofiles
import asyncio
import os
import random  # For randint
import uhal
import argparse
import sys
import time
from time import sleep

#IPB_PATH = "ipbusudp-2.0://192.168.0.10:50001?max_payload_size=1500"
IPB_PATH = "ipbusudp-2.0://192.168.0.10:50001"
ADR_TABLE = "./address_table/generic/etl_test_fw.xml"

def stream_daq(rb=0, l1a_rate=1000, meas_time=10, superblock=100, block=255):

    uhal.disableLogging()
    hw = uhal.getDevice("kcu105_daq", IPB_PATH, "file://" + ADR_TABLE)

    rate_setting = l1a_rate / 25E-9 / (0xffffffff) * 10000

    hw.getNode(f"SYSTEM.L1A_DELAY").write(0)
    hw.dispatch()

    hw.getNode(f"SYSTEM.QINJ_MAKES_L1A").write(0)
    hw.dispatch()

    # reset fifo
    hw.getClient().write(hw.getNode(f"READOUT_BOARD_{rb}.FIFO_RESET").getAddress(), 0x1)
    hw.dispatch()

    # set l1a rate
    hw.getNode("SYSTEM.L1A_RATE").write(int(rate_setting))
    hw.dispatch()
    hw.getNode("SYSTEM.QINJ_RATE").write(0)
    hw.dispatch()

    start = time.time()

    data = []

    with open("output/output.dat", mode="wb") as f:
        while start + meas_time > time.time():
        #for i in range(loops):
            try:

                # figure out how many blocks to read
                occupancy = hw.getNode(f"READOUT_BOARD_{rb}.RX_FIFO_OCCUPANCY").read()
                hw.dispatch()
                num_blocks_to_read = occupancy.value() // block


                # read them
                if (num_blocks_to_read):
                    reads = num_blocks_to_read * [hw.getNode("DAQ_RB0").readBlock(block)]
                    hw.dispatch()
                    for read in reads:
                        data += read.value()

            except uhal._core.exception:
                print("uhal UDP error in daq")

        timediff = time.time() - start
        speed = 32*len(data)  / timediff / 1E6
        occupancy = hw.getNode(f"READOUT_BOARD_{rb}.RX_FIFO_OCCUPANCY").read()
        lost = hw.getNode(f"READOUT_BOARD_{rb}.RX_FIFO_LOST_WORD_CNT").read()
        rate = hw.getNode(f"READOUT_BOARD_{rb}.PACKET_RX_RATE").read()
        l1a_rate_cnt = hw.getNode("SYSTEM.L1A_RATE_CNT").read()
        hw.dispatch()

        print("L1A rate = %f kHz" % (l1a_rate_cnt.value()/1000.0))
        print("Occupancy=%d words" % occupancy.value())
        print("Lost events=%d events" % lost.value())
        print("Packet rate=%d Hz" % rate.value())
        print("Speed = %f Mbps" % speed)

        # write to disk
        f.write(struct.pack('<{}I'.format(len(data)), *data))

    hw.getNode("SYSTEM.L1A_RATE").write(0)
    hw.dispatch()

    hw.getClient().write(hw.getNode(f"READOUT_BOARD_{rb}.FIFO_RESET").getAddress(), 0x1)
    hw.dispatch()

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--l1a_rate', action='store', default=1000, type=int, help="L1A rate in Hz")
    argParser.add_argument('--meas_time', action='store', default=10, type=int, help="Time in [s] to take data")
    args = argParser.parse_args()

    stream_daq(l1a_rate=args.l1a_rate, meas_time=args.meas_time)
