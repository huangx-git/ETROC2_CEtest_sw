#!/usr/bin/env python3
import json
import awkward as ak
import argparse
import numpy as np
import hist
import os
import matplotlib.pyplot as plt
import mplhep as hep
plt.style.use(hep.style.CMS)

if __name__ == '__main__':

    filelist = os.listdir(f"../output/Threshold_scan/")
    # intensities = [15 , 20 , 25 , 30 , 35 , 40 , 45 , 50 , 55 , 60 , 65 , 70 , 75 , 80]
    # indices     = [225, 226, 227, 228, 209, 217, 211, 218, 219, 220, 221, 222, 223, 224]

    # intensities = [90 , 91 , 92 , 93 , 94 , 95 , 96 , 97 , 98 , 99 , 100]
    # indices     = [232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242]

    intensities = [90 , 93 , 96 , 100]
    indices     = [232, 235, 238, 242]

    # mean_toa = [[],[],[],[]]
    # std_toa  = [[],[],[],[]]
    # mean_tot = [[],[],[],[]]
    # std_tot  = [[],[],[],[]]
    # mean_cal = [[],[],[],[]]
    # std_cal  = [[],[],[],[]]

    pixels = range(4)
    params = ["nhits"]
    # assert len(filelist) == len(intensities)
    fig, ax = plt.subplots()
    for f_index, file in enumerate(indices):
        # with open(f"../output/Intensities/Data_{file}.json", "r") as f:
        with open(f"../output/Threshold_scan/Data_{file}.json", "r") as f:
            res = json.load(f)
        events = ak.from_json(res)
        for param in params:
            nhits_axis = hist.axis.Regular(bins = 6, start = -0.5, stop = 5.5, name='n') # , label=f"vth: {intensities[f_index]}")
            nhits_hist = hist.Hist(nhits_axis)
            nhits_hist.fill(n=events[param])
            nhits_hist.plot1d(ax=ax, label = f"vth: {intensities[f_index]}", linewidth=3)
        ax.set_ylabel(r"$N_{Events}$")
        ax.set_xlabel(r"$N_{Hits}$")
    plt.legend()
    plt.show()
    fig.savefig("NHits_threshold_scan.png")
