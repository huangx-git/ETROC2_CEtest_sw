#!/usr/bin/env python3
import struct
import argparse
import numpy as np
from tamalero.FIFO import merge_words
from tamalero.DataFrame import DataFrame


if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--input', action='store', default='output/output_example.dat', help="Binary file to read from")
    args = argParser.parse_args()

    df = DataFrame('ETROC2')

    with open(args.input, 'rb') as f:
        bin_data = f.read()
        raw_data = struct.unpack('<{}I'.format(int(len(bin_data)/4)), bin_data)

    merged_data = merge_words(raw_data)
    unpacked_data = [ df.read(x) for x in merged_data ]

    # TODO
    # - run consistency checks on unpacked data
    # - do event merging
    # - convert data into a sensible format and write to root/parquet/... file
