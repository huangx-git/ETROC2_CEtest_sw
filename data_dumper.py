#!/usr/bin/env python3
import struct
import argparse
import numpy as np
import awkward as ak
import json
from tamalero.DataFrame import DataFrame
from emoji import emojize
import os

here = os.path.dirname(os.path.abspath(__file__))

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
    argParser.add_argument('--rbs', action='store', default='0', help="RB numbers")
    argParser.add_argument('--skip_trigger_check', action='store_true', help="Skip the double trigger check.")
    argParser.add_argument('--verbose', action='store_true', help="Print every event number.")
    argParser.add_argument('--force', action='store_true', help="Don't care about inconsistencies, force produce output.")
    args = argParser.parse_args()

    rbs = args.rbs.split(',')

    verbose = args.verbose
    df = DataFrame('ETROC2')

    do_double_trigger_check = not args.skip_trigger_check

    events_per_rb = []
    all_runs_good = True

    for irb, rb in enumerate(rbs):

        f_in = f'{here}/ETROC_output/output_run_{args.input}_rb{rb}.dat'

        with open(f_in, 'rb') as f:
            print("Reading from {}".format(f_in))
            bin_data = f.read()
            raw_data = struct.unpack('<{}I'.format(int(len(bin_data)/4)), bin_data)

        merged_data = merge_words(raw_data)
        unpacked_data = map(df.read, merged_data)

        event       = []
        counter_h   = []  # double check the number of headers
        counter_t   = []  # double check the number of trailers
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
        trailer_counter = 0


        headers = []
        trailers = []
        i = 0
        l1a = -1
        bcid_t = 9999
        skip_event = False
        skip_counter = 0
        bad_run = False


        uuid = []

        for t, d in unpacked_data:
            sus = False
            if t == 'header':
                hit_counter = 0
                uuid_tmp = d['l1counter'] | d['bcid']<<8
                headers.append(d['raw'])
                header_counter += 1
                #if (abs(d['bcid']-bcid_t)<50) and (d['bcid'] - bcid_t)>0 and not (d['bcid'] == bcid_t):
                #    skip_event = True
                #    print("Skipping event")
                #    continue
                if d['l1counter'] == l1a:
                    # this just skips additional headers for the same event
                    counter_h[-1] += 1
                    raw[-1].append(d['raw'])
                    if skip_event:
                        #print("Skipping event (same l1a counter)", d['l1counter'], d['bcid'], bcid_t)
                        continue
                    pass
                #elif d['l1counter'] < l1a and d['l1counter']!=0:
                # # NOTE this part is experimental, and removes duplicate events
                # # However, we should instead re-implement full consistency checks of header - data - trailer style
                #    skip_event = True
                #    print("Skipping event", d['l1counter'], d['bcid'], bcid_t)

                else:
                    if uuid_tmp in uuid and abs(i - np.where(np.array(uuid) == uuid_tmp)[0][-1]) < 150:
                        #print("Skipping duplicate event")
                        skip_counter += 1
                        skip_event = True
                        continue
                    else:
                        uuid.append(d['l1counter'] | d['bcid']<<8)
                    #if (abs(d['bcid']-bcid_t)<40) and (d['bcid'] - bcid_t)>0 and not (d['bcid'] == bcid_t):
                    #if (abs(d['bcid']-bcid_t)<500) and (d['bcid'] - bcid_t)>0 and not (d['bcid'] == bcid_t):
                    if (((abs(d['bcid']-bcid_t)<150) or (abs(d['bcid']+3564-bcid_t)<50)) and not (d['bcid'] == bcid_t) and do_double_trigger_check):
                        skip_event = True
                        #print("Skipping event", d['l1counter'], d['bcid'], bcid_t)
                        skip_counter += 1
                        continue
                    else:
                        skip_event = False
                    bcid_t = d['bcid']
                    if (abs(l1a - d['l1counter'])>1) and abs(l1a - d['l1counter'])!=255 and verbose:
                        print("SUS")
                        sus = True
                    l1a = d['l1counter']
                    event.append(i)
                    counter_h.append(1)
                    counter_t.append(0)
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
                    bcid.append([d['bcid']])
                    counter_a.append([])
                    i += 1
                    if verbose or sus:
                        print("New event:", l1a, i, d['bcid'])

            if t == 'data' and not skip_event:
                hit_counter += 1
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
                if nhits[-1] > 256:
                    print("This event already has more than 256 events. Breaking.")
                    bad_run = True
                    break

            if t == 'trailer':
                trailers.append(d['raw'])
                trailer_counter += 1
                if not skip_event:
                    counter_t[-1] += 1
                    if hit_counter > 0:
                        chipid[-1].append(hit_counter*d['chipid'])
                    nhits_trail[-1].append(d['hits'])
                    raw[-1].append(d['raw'])
                    crc[-1].append(d['crc'])


        if not bad_run or args.force:
            print("Zipping")
            events = ak.Array({
                'event': event,
                'l1counter': l1counter,
                'nheaders': counter_h,
                'ntrailers': counter_t,
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
                'nhits_trail': ak.sum(ak.Array(nhits_trail), axis=-1),
            })

            total_events = len(events)
            # NOTE the check below is only valid for single ETROC
            consistent_events = len(events[((events.nheaders==2)&(events.ntrailers==2)&(events.nhits==events.nhits_trail))])

            print(total_events, consistent_events)

            print(f"Done with {len(events)} events. " + emojize(":check_mark_button:"))
            print(f" - skipped {skip_counter/events.nheaders[0]} events that were identified as duplicate / spurious " + emojize(":check_mark_button:"))
            if header_counter == trailer_counter:
                print(f" - found same number of headers and trailers! " + emojize(":check_mark_button:"))
            else:
                print(f" - found {header_counter} headers and {trailer_counter} trailers. Please check. " + emojize(":warning:"))
                # print(skipped_events)

            with open(f"{here}/ETROC_output/output_run_{args.input}_rb{rb}.json", "w") as f:
                json.dump(ak.to_json(events), f)

            print(f"Mean number of hits:", np.mean(events.nhits))

            # make some plots
            import matplotlib.pyplot as plt
            import mplhep as hep
            plt.style.use(hep.style.CMS)

            hits = np.zeros([16, 16])

            for ev in events:
                for row, col in zip(ev.row, ev.col):
                    hits[row][col] += 1

            fig, ax = plt.subplots(1,1,figsize=(7,7))
            cax = ax.matshow(hits)
            ax.set_ylabel(r'$Row$')
            ax.set_xlabel(r'$Column$')
            fig.colorbar(cax,ax=ax)
            fig.savefig(f"{here}/ETROC_output/output_run_{args.input}_rb{rb}_heatmap.pdf")
            fig.savefig(f"{here}/ETROC_output/output_run_{args.input}_rb{rb}_heatmap.png")

            events_per_rb.append(events)
        else:
            print("Bad run detected. Not creating a json file.")
            all_runs_good = False
            if os.path.isfile(f"{here}/ETROC_output/output_run_{args.input}_rb{rb}.json"):
                os.remove(f"{here}/ETROC_output/output_run_{args.input}_rb{rb}.json")


    if len(events_per_rb)>1 and False:
        merged_events = events_per_rb[0]
        if all_runs_good:
            event_l     = []
            counter_h   = []  # double check the number of headers
            counter_t   = []  # double check the number of trailers
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
            trailer_counter = 0
            for i, events_list in enumerate(events_per_rb):
                #print ('rb', i)
                j = 0
                for event in events_list:
                    #print ('event', j)
                    if i == 0:
                        event_l.append(j)
                        l1counter.append(event.l1counter)
                        counter_h.append(event.nheaders)
                        counter_t.append(event.ntrailers)
                        nhits.append(event.nhits)
                        nhits_trail.append(event.nhits_trail)
                        counter_a.append(list(event.counter_a))

                        row.append(list(event.row))
                        col.append(list(event.col))
                        toa_code.append(list(event.toa_code))
                        tot_code.append(list(event.tot_code))
                        cal_code.append(list(event.cal_code))
                        crc.append(list(event.crc))
                        raw.append(list(event.raw))
                        elink.append(list(event.elink))
                        chipid.append(list(event.chipid))
                        bcid.append(list(event.bcid))
                    else:
                        if not event.l1counter == events_per_rb[0][j].l1counter:
                            j += 1
                            print("skipped a spurious event", event.l1counter, j, events_per_rb[0][j].l1counter)
                            continue
                        counter_h[j] += (event.nheaders)
                        counter_t[j] += (event.ntrailers)
                        nhits[j] += (event.nhits)
                        nhits_trail[j] += (event.nhits_trail)

                        counter_a[j] += list(event.counter_a)
                        row[j] += list(event.row)
                        col[j] += list(event.col)
                        toa_code[j] += list(event.toa_code)
                        tot_code[j] += list(event.tot_code)
                        cal_code[j] += list(event.cal_code)
                        crc[j] += list(event.crc)
                        raw[j] += list(event.raw)
                        elink[j] += list(event.elink)
                        chipid[j] += list(event.chipid)
                        bcid[j] += list(event.bcid)
                    j += 1


            print("Zipping, again")
            events = ak.Array({
                'event': event_l,
                'l1counter': l1counter,
                'nheaders': counter_h,
                'ntrailers': counter_t,
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
                'nhits': nhits,
                'counter_a': counter_a,
                #'nhits_trail': ak.sum(ak.Array(nhits_trail), axis=-1),
            })

            # call this rb0 for consistency
            with open(f"{here}/ETROC_output/output_run_{args.input}_rb0.json", "w") as f:
                json.dump(ak.to_json(events), f)
