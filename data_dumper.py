#!/usr/bin/env python3
import struct
import argparse
import numpy as np
import uproot
import awkward as ak
import json
from tamalero.DataFrame import DataFrame
import ROOT as rt
import pdb

def merge_words(res):
    empty_frame_mask = np.array(res[0::2]) > (2**8)  # masking empty fifo entries
    len_cut = min(len(res[0::2]), len(res[1::2]))  # ensuring equal length of arrays downstream
    if len(res) > 0:
        return list (np.array(res[0::2])[:len_cut][empty_frame_mask[:len_cut]] | (np.array(res[1::2]) << 32)[:len_cut][empty_frame_mask[:len_cut]])
    else:
        return []

#class Event:
#    def __init__(self, event, l1counter, bcid, raw):
#        self.event = event
#        self.l1counter = l1counter
#        self.bcid = bcid
#        self.row = []
#        self.col = []
#        self.tot_code = []
#        self.toa_code = []
#        self.cal_code = []
#        self.elink = []
#        self.nhits = 0
#        self.nhits_trailer = 0
#        self.chipid = []
#        self.raw = [raw]
#
#
#    def add_hit(self, row, col, tot_code, toa_code, cal_code, elink, raw):
#        self.row.append(row)
#        self.col.append(col)
#        self.tot_code.append(tot_code)
#        self.toa_code.append(toa_code)
#        self.cal_code.append(cal_code)
#        self.elink.append(elink)
#        self.raw.append(raw)
#        self.nhits += 1
#
#    def parse_trailer(self, chipid, hits, crc, raw):
#        self.nhits_trailer += hits
#        self.chipid += [chipid]*hits
#        self.crc = crc
#        self.raw.append(raw)

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--input', action='store', default='output_test2', help="Binary file to read from")
    argParser.add_argument('--nevents', action='store', default=100, help="Number of events")
    args = argParser.parse_args()

    df = DataFrame('ETROC2')

    f_in = f'ETROC_output/output_run_{args.input}.dat'

    with open(f_in, 'rb') as f:
        print("Reading from {}".format(f_in))
        bin_data = f.read()
        raw_data = struct.unpack('<{}I'.format(int(len(bin_data)/4)), bin_data)

    merged_data = merge_words(raw_data)
    unpacked_data = map(df.read, merged_data)

    event       = []
    l1counter   = []
    row         = []
    col         = []
    tot_code    = []
    toa_code    = []
    cal_code    = []
    elink       = []
    raw         = []
    nhits       = []
    nhits_trail = []
    chipid      = []
    crc         = []
    bcid        = []
    counter_a   = []

    header_counter = 0

    header_counter_l1a = 0
    trailer_counter_l1a = 0
    data_counter_l1a = 0
    i = 0
    l1a = -1
    # pdb.set_trace()
    datas = []
    headers = []
    deltas = []
    counter = 0
    for t, d in unpacked_data:
        if i > 0 and t == 'header':
            # delta_bcid = abs((float(d['bcid']) % 3564) - (bcid[i-1] % 3564))
            if bcid[i-1] > d['bcid']: # If it performed a roll | --------------.---|---.---.---------
                delta_bcid = abs(float(d['bcid'] + (3564 - bcid[i-1])))
            else:
                delta_bcid = abs(float(d['bcid'] - bcid[i-1]))
            deltas.append(delta_bcid)
            if (delta_bcid < 500): # or (delta_bcid > 1500 and delta_bcid < 2500)):
                continue

        if t == 'header':
            header_counter += 1
            if d['l1counter'] == l1a:
                pass
            else:
                datas.append(data_counter_l1a)
                headers.append(l1a)
                data_counter_l1a = 0
                l1a = int(d['l1counter'])
                event.append(i)
                l1counter.append(int(d['l1counter']))
                row.append([])
                col.append([])
                tot_code.append([])
                toa_code.append([])
                cal_code.append([])
                elink.append([])
                raw.append([d['raw']])
                nhits.append(0)
                nhits_trail.append([])
                chipid.append([])
                crc.append([])
                # bcid.append([])
                counter_a.append([])
                i += 1
                # bcid[-1].append(float(d['bcid']))
                bcid.append(int(d['bcid']))

        if t == 'data':
            data_counter_l1a += 1
            # print(float(d['elink']))
            if (float(d['elink']) != 28.0):
                # print(float(d['elink']))
                print("Wrong elink: ", d['elink'])
            if 'tot' in d:
                # print(d['toa'])
                # print(d['tot'])
                # print(d['cal'])
                tot_code[-1].append(float(d['tot']))
                toa_code[-1].append(float(d['toa']))
                cal_code[-1].append(float(d['cal']))
            elif 'counter_a' in d:
                counter_a[-1].append(float(d['counter_a']))
            elif 'counter_b' in d:
                pass
            row[-1].append(int(d['row_id']))
            col[-1].append(int(d['col_id']))
            elink[-1].append(float(d['elink']))
            raw[-1].append(d['raw'])
            nhits[-1] += 1

        if t == 'trailer':
            chipid[-1].append(d['hits']*d['chipid'])
            nhits_trail[-1].append(d['hits']) # check if the sum is the number of data words.
            # raw[-1].append(d['raw'])
            crc[-1].append(d['crc'])
    # print("Counter: ", counter)
    events = ak.Array({
        'event': event,
        'l1counter': l1counter,
        'row': row,
        'col': col,
        'tot_code': tot_code,
        'toa_code': toa_code,
        'cal_code': cal_code,
        'elink': elink,
        'raw': raw,
        'crc': crc,
        'chipid': chipid,
        'bcid': bcid,
        'counter_a': counter_a,
        'nhits': nhits,
        'nhits_trail': nhits_trail,
    })
    # events = ak.Array([i for i in events if (len(i['elink']) == i["nhits"])]) # if (len(i["elink"]) != 0) 
    datas = np.array(datas)
    # pdb.set_trace()
    # print(len(deltas))
    with open(f"ETROC_output/output_run_{args.input}.json", "w") as f:
        json.dump(ak.to_json(events), f)
