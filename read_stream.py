from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import header, make_version_header
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame

from tamalero.SCA import SCA_CONTROL

import os
import time
import random
import sys
import numpy as np
from yahist import Hist1D, Hist2D

def build_events(dump, ETROC="ETROC1"):
    df = DataFrame(ETROC)

    events = []
    last_type = "filler"
    for word in dump:
        data_type, res = df.read(word)
        if data_type == "header" and last_type in ["trailer", "filler"]:
            events.append({"header": [], "data": [], "trailer": []})
        elif data_type == "filler":
            events.append({"filler": []})
        if len(events) > 0:
            events[-1][data_type].append(res)
        
        last_type = data_type

    return events

if __name__ == '__main__':

    import argparse

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Reset pattern checker?")
    argParser.add_argument('--read_fifo', action='store', default=2, help='Read 3000 words from link N')
    argParser.add_argument('--etroc', action='store', default='ETROC1', help='Select ETROC version')
    argParser.add_argument('--triggers', action='store', default=10, help='How many L1As?')
    args = argParser.parse_args()

    kcu = KCU(name="my_device",
              ipb_path="ipbusudp-2.0://%s:50001"%args.kcu,
              adr_table="module_test_fw/address_tables/etl_test_fw.xml")

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0))

    
    fifo_link = int(args.read_fifo)

    events = []
    fifo = FIFO(rb_0, elink=fifo_link, ETROC=args.etroc)
    fifo.set_trigger(
        # NOTE: this could also use the data format in the future
        words = [0x00, 0x00, 0x00, 0x5C, 0x3C] if args.etroc=="ETROC2" else [0x35, 0x55, 0x00, 0x00, 0x00],
        masks = [0x00, 0x00, 0xC0, 0xFF, 0xFF] if args.etroc=="ETROC2" else [0xFF, 0xFF, 0x00, 0x00, 0x00],
    )
    
    for i in range(int(args.triggers)):
        #print(i)
        fifo.reset()
        test = fifo.giant_dump(block=300, format=False, align=(args.etroc=='ETROC1'))
        events += build_events(test, ETROC=args.etroc)

    hits = np.zeros((16,16))
    nhits = Hist1D(bins=np.linspace(-0.5,20.5,22))
    toa = Hist1D(bins=np.linspace(-0.5,2**10,50))
    tot = Hist1D(bins=np.linspace(0,2**9,50))
    #hit_matrix = Hist2D(bins=(np.linspace(-0.5,15.5,17), np.linspace(-0.5,15.5,17)))

    for event in events:
        if 'filler' in event: continue
        try:
            nhits.fill([event['trailer'][0]['hits']])
            if event['trailer'][0]['hits'] > 0:
                for d in event['data']:
                    row, col = d['row_id'], d['col_id']
                    if not args.etroc=='ETROC2':  # NOTE: not working for ETROC2 yet
                        toa.fill([d['toa']])
                        tot.fill([d['tot']])
                    hits[row, col] += 1
        except IndexError:
            pass
            #print ("Skipping incomplete event")
        # FIXME: consistency checks are missing


    import matplotlib.pyplot as plt
    import mplhep as hep

    plt.style.use(hep.style.CMS)  # or ATLAS/LHCb
    
    fig, ax = plt.subplots(1,1,figsize=(7,7))
    nhits.plot(show_errors=True, color="blue", label='Number of hits')
    ax.set_ylabel('Count')
    ax.set_xlabel('Hits')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'nhits_ETROC1'
    
    fig.savefig(os.path.join("{}.pdf".format(name)))
    fig.savefig(os.path.join("{}.png".format(name)))


    fig, ax = plt.subplots(1,1,figsize=(7,7))
    toa.plot(color="blue", histtype="step")
    ax.set_ylabel('Count')
    ax.set_xlabel('TOA')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'TOA'
    
    fig.savefig(os.path.join("{}.pdf".format(name)))
    fig.savefig(os.path.join("{}.png".format(name)))


    fig, ax = plt.subplots(1,1,figsize=(7,7))
    tot.plot(color="blue", histtype="step")
    ax.set_ylabel('Count')
    ax.set_xlabel('TOT')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'TOT'
    
    fig.savefig(os.path.join("{}.pdf".format(name)))
    fig.savefig(os.path.join("{}.png".format(name)))


    fig, ax = plt.subplots(1,1,figsize=(7,7))
    hit_matrix = Hist2D.from_bincounts(hits, bins=(np.linspace(-0.5,15.5,17), np.linspace(-0.5,15.5,17)))
    hit_matrix.plot(logz=False, cmap="cividis")
    ax.set_ylabel('Row')
    ax.set_xlabel('Column')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'hit_matrix'
    
    fig.savefig(os.path.join("{}.pdf".format(name)))
    fig.savefig(os.path.join("{}.png".format(name)))
    

    #try:
    #    hex_dump = fifo.giant_dump(3000,255)
    #except:
    #    print ("Dispatch failed, trying again.")
    #    hex_dump = fifo.giant_dump(3000,255)

    #print (hex_dump)
    #fifo.dump_to_file(fifo.wipe(hex_dump, trigger_words=[]))  # use 5 columns --> better to read for our data format
