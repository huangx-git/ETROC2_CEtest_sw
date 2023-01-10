#!/usr/bin/env python3
import struct
import argparse
import numpy as np
import awkward as ak
import pandas as pd
# from tamalero.FIFO import merge_words
from tamalero.DataFrame import DataFrame

def merge_words(res):
    empty_frame_mask = np.array(res[0::2]) > (2**8)  # masking empty fifo entries
    len_cut = min(len(res[0::2]), len(res[1::2]))  # ensuring equal length of arrays downstream
    if len(res) > 0:
        return list (np.array(res[0::2])[:len_cut][empty_frame_mask[:len_cut]] | (np.array(res[1::2]) << 32)[:len_cut][empty_frame_mask[:len_cut]])
    else:
        return []


if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--input', action='store', default='output/output_example.dat', help="Binary file to read from")
    args = argParser.parse_args()

    df = DataFrame('ETROC2')

    with open(args.input, 'rb') as f:
        print("Reading from {}".format(args.input))
        bin_data = f.read()
        raw_data = struct.unpack('<{}I'.format(int(len(bin_data)/4)), bin_data)

    merged_data = merge_words(raw_data)
    unpacked_raw_data = [ df.read(x) for x in raw_data ]
    unpacked_data = [ df.read(x) for x in merged_data ]
    
    #TODO: this is a bit convoluted, at some point it should be rewritten
    # gymnastic to get an awkward array with header,[datas],trailer per each row
    tuple_df = pd.DataFrame.from_dict(unpacked_data)
    data_df = pd.json_normalize(tuple_df[1][:])
    data_df["data_type"] = tuple_df[0][:]
    event_df = data_df.groupby(data_df["elink"].diff().ne(0).cumsum(),as_index=False).agg(list)
    event_ak = ak.Array({name: event_df[name].values for name in event_df.columns})

    #cleaning the df structure  
    for f in event_ak.fields: # Here I am merging the fields that are identical across header,hits,trailer 
        maxes = ak.max(event_ak[f],axis=-1)
        minmus = ak.min(event_ak[f],axis =-1 )
        if ak.all( maxes == minmus ):
            event_ak[f] = minmus

    event_ak["l1counter"] = ak.sum(ak.nan_to_num(event_ak["l1counter"], nan=0.0),axis=-1 )
    event_ak["status"] = ak.sum(ak.nan_to_num(event_ak["status"], nan=0.0),axis=-1 )
    event_ak["chipid"] = ak.sum(ak.nan_to_num(event_ak["chipid"], nan=0.0),axis=-1 )
    event_ak["hits"] = ak.sum(ak.nan_to_num(event_ak["hits"], nan=0.0),axis=-1 )
    event_ak["type"] = ak.sum(ak.nan_to_num(event_ak["type"], nan=0.0),axis=-1 )
    event_ak["crc"] = ak.sum(ak.nan_to_num(event_ak["crc"], nan=0.0),axis=-1 )

    for i,l1c in enumerate(event_ak["l1counter"]):
        print (i, " " ,l1c)
    
    l1a0 = event_ak["l1counter"] == 0
    weird_dt = ak.where("header" not in event_ak["data_type"]

    l1_ak = event_ak
    for ev in l1_ak:
        for f in l1_ak.fields:
            print (f, " " ,ev[f])
        print(" ")
    
    # merging events

    sorted_ak = event_ak[ak.argsort(event_ak["l1counter"])]


    # TODO
    # - run consistency checks on unpacked data
    # - do event merging
    # - convert data into a sensible format and write to root/parquet/... file  
