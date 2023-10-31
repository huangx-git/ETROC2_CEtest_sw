#!/usr/bin/env python3
import struct
import argparse
import numpy as np
import awkward as ak
import ROOT as rt
import json
import pdb
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
                # raw.append([d['raw']])
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
            # raw[-1].append(d['raw'])
            nhits[-1] += 1

        if t == 'trailer':
            chipid[-1].append(d['hits']*d['chipid'])
            nhits_trail[-1].append(d['hits'])
            # raw[-1].append(d['raw'])
            crc[-1].append(d['crc'])

    print("Zipping")
    obj = {
        'event': event,
        'l1counter': l1counter,
        'row': row,
        'col': col,
        'tot_code': tot_code,
        'toa_code': toa_code,
        'cal_code': cal_code,
        'elink': elink,
        # 'raw': raw,
        'crc': crc,
        'chipid': chipid,
        'bcid': bcid,
        'counter_a': counter_a,
        'nhits': nhits,
        'nhits_trail': nhits_trail,
    }

    events = ak.Array(obj)
    with rt.TFile.Open(f"output/{args.input}.root", "recreate") as f:
        tree = rt.TTree("events", "events")
        for l in obj:
            vec = rt.std.vector[float]()
            tree.Branch(l, vec)
            for v in obj[l]:
                is_list = False
                if type(v) is list:
                    vec.clear()
                    vec.reserve(len(v))
                    for v0 in v:
                        vec.push_back(v0)
                    tree.Fill()
                    is_list = True
                else:
                    vec.push_back(v)
                if not is_list:
                    tree.Fill()
            f.WriteObject(tree, "events")

