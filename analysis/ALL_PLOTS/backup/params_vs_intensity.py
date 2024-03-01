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

    intensities = [90 , 91 , 92 , 93 , 94 , 95 , 96 , 97 , 98 , 99 , 100]
    indices     = [232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242]

    mean_toa = [[],[],[],[]]
    std_toa  = [[],[],[],[]]
    mean_tot = [[],[],[],[]]
    std_tot  = [[],[],[],[]]
    mean_cal = [[],[],[],[]]
    std_cal  = [[],[],[],[]]
    pixels = range(4)
    params = ["toa", "tot"]
    # assert len(filelist) == len(intensities)
    for f_index, file in enumerate(indices):
        # with open(f"../output/Intensities/Data_{file}.json", "r") as f:
        with open(f"../output/Threshold_scan/Data_{file}.json", "r") as f:
            res = json.load(f)
        events = ak.from_json(res)
        for param in params:
            for pixel in pixels:
                # plot_dir = f"../results/{param}_intensity.png"
                plot_dir = f"../results/{param}_threshold_scan.png"
                if not os.path.isdir(plot_dir):
                    os.makedirs(plot_dir)
                events['bin'] = 3.125 / events.cal_code
                events['toa'] = 12.5 - events.bin * events.toa_code
                events['tot'] = (2*events.tot_code - np.floor(events.tot_code/32))*events.bin
                # toa = np.nan_to_num(ak.flatten(events.toa), nan=0, posinf=0, neginf=0)
                # toa = toa[((toa>7)&(toa<9))]
                # toa_mean = np.mean(toa)
                variable = events[param][((events.nhits==4)&(events.row==15)&(events.col==pixel))]
                variable = variable[variable < 100000]
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
        print(mean_toa[pixel])
        ax[0].errorbar(intensities, mean_toa[pixel], yerr = std_toa[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o-")
        # ax[0].plot(intensities, mean_toa[pixel]) # , yerr = std_toa[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o"
    ax[0].set_ylabel("Mean TOA")
    ax[0].set_xlabel("Intensity (%)")
    ax[0].legend()
    # plt.legend()
    # plt.show()
    # fig.savefig("toa_vs_int.png")
    # TOT
    for pixel in pixels:
        ax[1].errorbar(intensities, mean_tot[pixel], yerr = std_tot[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o-")
        # ax[1].plot(intensities, mean_tot[pixel]) # , yerr = std_tot[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o"
    ax[1].set_ylabel("Mean TOT")
    ax[1].set_xlabel("Intensity (%)")
    ax[1].legend()
    # plt.title("Calculation of mean TOA and TOT for different intensities.")
    plt.show()
    fig.savefig("param_vs_int.png")
    # # CAL
    # for pixel in pixels:
    #     ax[2].errorbar(mean_cal[pixel], intensities, yerr = std_cal[pixel], label = f'Row: 15, Col: {pixel}')
    # plt.legend()
    # plt.show()
    # fig.savefig("cal_vs_int.png")
