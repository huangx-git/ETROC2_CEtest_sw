#!/usr/bin/env python3
import json
import awkward as ak
import argparse
import numpy as np
import hist
import os
import matplotlib.pyplot as plt
import mplhep as hep
import glob
plt.style.use(hep.style.CMS)

if __name__ == '__main__':

    # filelist = os.listdir(f"../output/Threshold_scan_17p4/")
    # intensities = [15 , 20 , 25 , 30 , 35 , 40 , 45 , 50 , 55 , 60 , 65 , 70 , 75 , 80]
    # indices     = [225, 226, 227, 228, 209, 217, 211, 218, 219, 220, 221, 222, 223, 224]

    # intensities = [90 , 91 , 92 , 93 , 94 , 95 , 96 , 97 , 98 , 99 , 100]
    # indices     = [232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242]

    # intensities = [15,25,35 ,45 ,55 ,65 ,75 ]
    intensities = [15, 25, 35, 45, 55, 65, 75]
    thresholds  = [90,95,100,105,110,115,120]
    indices     = [
        [304, 305, 306, 307, 308, 309, 310],
        [297, 298, 299, 300, 301, 302, 303],
        [290, 291, 292, 293, 294, 295, 296],
        [283, 284, 285, 286, 287, 288, 289],
        [276, 277, 278, 279, 280, 281, 282],
        [269, 270, 271, 272, 273, 274, 275],
        [262, 263, 264, 265, 266, 267, 268],
    ]

    pixels = range(4)
    params = ["toa", "tot"]

    for i, intensity in enumerate(intensities):
        mean_toa = [[] for i in pixels]
        std_toa  = [[] for i in pixels]
        mean_tot = [[] for i in pixels]
        std_tot  = [[] for i in pixels]
        mean_cal = [[] for i in pixels]
        std_cal  = [[] for i in pixels]
        for t, threshold in enumerate(thresholds):
            index = indices[i][t]
            inputname = glob.glob(f"../output/Threshold_scan_{intensity}/output_run_{index}_time_*.json")[0]
            with open(inputname, "r") as f:
                res = json.load(f)
            events = ak.from_json(res)
            for param in params:
                for pixel in pixels:
                    # plot_dir = f"../results/{param}_intensity.png"
                    # plot_dir = f"../results/{param}_threshold_scan.png"
                    # if not os.path.isdir(plot_dir):
                    #     os.makedirs(plot_dir)
                    # print(events.cal_code)
                    events['bin'] = 3.125 / events.cal_code
                    events['toa'] = 12.5 - events.bin * events.toa_code
                    events['tot'] = (2*events.tot_code - np.floor(events.tot_code/32))*events.bin
                    variable = events[param][((events.nhits==4)&(events.row==15)&(events.col==pixel))]
                    variable = variable[np.abs(variable) < 100000]
                    if np.abs(np.mean(variable)) == np.inf:
                        print(variable)
                    mean_variable = np.mean(variable)
                    std_variable = np.std(variable) / len(variable)
                    if param == "toa":
                        mean_toa[pixel].append(mean_variable)
                        std_toa[pixel].append(std_variable)
                    elif param == "tot":
                        mean_tot[pixel].append(mean_variable)
                        std_tot[pixel].append(std_variable)
                    elif param == "cal":
                        mean_cal[pixel].append(mean_variable)
                        stc_cal[pixel].append(std_variable)
        a = 10
        fig, ax = plt.subplots(1, len(params), figsize = (a * len(params), a))

        # TOA
        for pixel in pixels:
            # print(mean_toa[pixel])
            ax[0].errorbar(thresholds, mean_toa[pixel], yerr = std_toa[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o-")
            print(mean_toa[pixel])
        ax[0].set_ylabel("Mean TOA")
        ax[0].set_xlabel("Threshold DAC values")
        ax[0].legend()

        # TOT
        for pixel in pixels:
            ax[1].errorbar(thresholds, mean_tot[pixel], yerr = std_tot[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o-")
            print(mean_tot[pixel])
        ax[1].set_ylabel("Mean TOT")
        ax[1].set_xlabel("Threshold DAC values")
        ax[1].legend()
        plt.show()
        fig.savefig(f"toa_tot_vth_{intensity}.png")
        print()

