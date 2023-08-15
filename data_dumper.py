#!/usr/bin/env python3
import struct
import argparse
import numpy as np
import awkward as ak
import json
from tamalero.DataFrame import DataFrame

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
    args = argParser.parse_args()

    df = DataFrame('ETROC2')

    f_in = f'output/{args.input}.dat'

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

    i = 0
    l1a = -1
    for t, d in unpacked_data:
        if t == 'header':
            header_counter += 1
            if d['l1counter'] == l1a:
                pass
            else:
                l1a = d['l1counter']
                event.append(i)
                l1counter.append(d['l1counter'])
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
                bcid.append([])
                counter_a.append([])
                i += 1

        if t == 'data':
            if 'tot' in d:
                tot_code[-1].append(d['tot'])
                toa_code[-1].append(d['toa'])
                cal_code[-1].append(d['cal'])
            elif 'counter_a' in d:
                bcid[-1].append(d['bcid'])
                counter_a[-1].append(d['counter_a'])
            elif 'counter_b' in d:
                pass
            row[-1].append(d['row_id'])
            col[-1].append(d['col_id'])
            elink[-1].append(d['elink'])
            raw[-1].append(d['raw'])
            nhits[-1] += 1

        if t == 'trailer':
            chipid[-1].append(d['hits']*d['chipid'])
            nhits_trail[-1].append(d['hits'])
            raw[-1].append(d['raw'])
            crc[-1].append(d['crc'])

    print("Zipping")
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

    with open(f"output/{args.input}.json", "w") as f:
        json.dump(ak.to_json(events), f)
