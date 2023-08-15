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
from tamalero.utils import get_kcu

#IPB_PATH = "ipbusudp-2.0://192.168.0.10:50001?max_payload_size=1500"
IPB_PATH = "ipbusudp-2.0://192.168.0.10:50001"
ADR_TABLE = "./address_table/generic/etl_test_fw.xml"

def get_occupancy(hw, rb):
    try:
        occupancy = hw.getNode(f"READOUT_BOARD_{rb}.RX_FIFO_OCCUPANCY").read()
        hw.dispatch()
        occ = occupancy.value()
    except uhal._core.exception:
        print("uhal UPDP error when trying to get occupancy. Returning 0.")
        occ = 0
    return occ * 4  # not sure where the factor of 4 comes from, but it's needed

def stream_daq(kcu, rb=0, l1a_rate=1000, run_time=10, superblock=100, block=250, run=1):

    uhal.disableLogging()
    hw = kcu.hw  #uhal.getDevice("kcu105_daq", IPB_PATH, "file://" + ADR_TABLE)

    rate_setting = l1a_rate / 25E-9 / (0xffffffff) * 10000

    # reset fifo
    hw.getClient().write(hw.getNode(f"READOUT_BOARD_{rb}.FIFO_RESET").getAddress(), 0x1)
    hw.dispatch()

    # set l1a rate
    hw.getNode("SYSTEM.L1A_RATE").write(int(rate_setting))
    hw.dispatch()

    start = time.time()

    data = []

    occupancy = 0
    f_out = f"output/output_run_{run}_time_{start}.dat"
    with open(f_out, mode="wb") as f:
        while start + run_time > time.time():
            num_blocks_to_read = 0
            occupancy = get_occupancy(hw, rb)
            num_blocks_to_read = occupancy // block

            # read the blocks
            if (num_blocks_to_read):
                try:
                    reads = num_blocks_to_read * [hw.getNode("DAQ_RB0").readBlock(block)]
                    hw.dispatch()
                    for read in reads:
                        data += read.value()
                except uhal._core.exception:
                    print("uhal UDP error in reading FIFO")

                # Write data to disk
                try:
                    f.write(struct.pack('<{}I'.format(len(data)), *data))
                    data = []
                except:
                    print("Error writing to file")

        print("Resetting L1A rate back to 0")
        hw.getNode("SYSTEM.L1A_RATE").write(0)
        hw.dispatch()

        # Read data that might still be in the FIFO
        occupancy = get_occupancy(hw, rb)
        print(f"Occupancy before last read: {occupancy}")
        reads = [hw.getNode("DAQ_RB0").readBlock(occupancy)]
        hw.dispatch()
        for read in reads:
            data += read.value()
        #print(data)


        #print(data)
        occupancy = get_occupancy(hw, rb)
        while occupancy>0:
            print("Found stuff in FIFO. This should not have happened!")
            num_blocks_to_read = occupancy // block
            last_block = occupancy % block
            if num_blocks_to_read > 0:
                print(occupancy, num_blocks_to_read, last_block)
            if (num_blocks_to_read or last_block):
                reads = num_blocks_to_read * [hw.getNode("DAQ_RB0").readBlock(block)]
                reads += [hw.getNode("DAQ_RB0").readBlock(last_block)]
                hw.dispatch()
                for read in reads:
                    data += read.value()
            occupancy = hw.getNode(f"READOUT_BOARD_{rb}.RX_FIFO_OCCUPANCY").read()
            hw.dispatch()

        # Get some stats
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


    hw.getClient().write(hw.getNode(f"READOUT_BOARD_{rb}.FIFO_RESET").getAddress(), 0x1)
    hw.dispatch()
    return f_out


if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default='192.168.0.10', help="KCU address")
    argParser.add_argument('--rb', action='store', default=0, type=int, help="RB number (default 0)")
    argParser.add_argument('--l1a_rate', action='store', default=1000, type=int, help="L1A rate in Hz")
    argParser.add_argument('--run_time', action='store', default=10, type=int, help="Time in [s] to take data")
    argParser.add_argument('--run', action='store', default=1, type=int, help="Run number")
    args = argParser.parse_args()

    rb = int(args.rb)
    kcu = get_kcu(args.kcu)

    print(f"Taking data now.\n ...")

    f_out = stream_daq(kcu, l1a_rate=args.l1a_rate, run_time=args.run_time, run=args.run)

    print(f"Run {args.run} has ended.")
    print(f"Stored data in file: {f_out}")
    # NOTE this would be the place to also dump the ETROC configs
