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
import uproot
plt.style.use(hep.style.CMS)

def array_mult(arr1, arr2):
    return ak.Array([arr1[i] * arr2[i] for i in range(len(arr1))])

if __name__ == '__main__':

    # filelist = os.listdir(f"../output/Threshold_scan_17p4/")
    # intensities = [15 , 20 , 25 , 30 , 35 , 40 , 45 , 50 , 55 , 60 , 65 , 70 , 75 , 80]
    # indices     = [225, 226, 227, 228, 209, 217, 211, 218, 219, 220, 221, 222, 223, 224]

    # intensities = [90 , 91 , 92 , 93 , 94 , 95 , 96 , 97 , 98 , 99 , 100]
    # indices     = [232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242]

    # intensities = [15,25,35 ,45 ,55 ,65 ,75 ]

    '''
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
    '''

    path = "/home/daq/ETROC2_Test_Stand/ScopeHandler/ScopeData/LecroyMerged"
    intensities = range(0, 11, 1)
    print(len(intensities))
    thresholds = [20]
    indices = [
        # range(10370, 10379, 1),
        # range(10379, 10388, 1)
        # [10389, 10390, 10391, 10392, 10393, 10401, 10404, 10396, 10397, 10398]
        [10498, 10496, 10494, 10492, 10491, 10490, 10491, 10489, 10488, 10487, 10485, 10484]
    ]
    print(len(indices[0]))

    pixels = range(1)
    params = ["toa", "tot"]
    mean_toa = [[] for p in pixels]
    std_toa  = [[] for p in pixels]
    mean_tot = [[] for p in pixels]
    std_tot  = [[] for p in pixels]
    mean_cal = [[] for p in pixels]
    std_cal  = [[] for p in pixels]
    for i, intensity in enumerate(intensities):

        for t, threshold in enumerate(thresholds):
            index = indices[t][i]
            # inputname = glob.glob(f"../output/Threshold_scan_{intensity}/output_run_{index}_time_*.json")[0]
            inputname = (f"{path}/run_{index}.root")
            print(inputname)
            # with open(inputname, "r") as f:
            events = uproot.open(inputname)["pulse"]
            events_obj = {}
            # events = ak.from_json(res)
            for param in params:
                for pixel in pixels:
                    # plot_dir = f"../results/{param}_intensity.png"
                    # plot_dir = f"../results/{param}_threshold_scan.png"
                    # if not os.path.isdir(plot_dir):
                    #     os.makedirs(plot_dir)

                    bins     = 3.125 / (events["cal_code"].array())
                    row      = events["row"     ].array()
                    col      = events["col"     ].array()
                    nhits    = events["nhits"   ].array()
                    toa_code = events["toa_code"].array()
                    tot_code = events["tot_code"].array()
                    cal_code = events["cal_code"].array()

                    # print(bins)
                    # print(toa_code)
                    # print(tot_code)
                    # print(cal_code)

                    toa = 12.5 - bins * toa_code # array_mult(bins, toa_code)
                    tot = (2*(tot_code) - np.floor((tot_code)/32)) / bins
                    # print((nhits==4)&(row==15)&(col==pixel))
                    # print(toa[(nhits==4)&(row==15)&(col==pixel)])
                    # print(tot[(nhits==4)&(row==15)&(col==pixel)])
                    # print(len((nhits==4)&(row==15)&(col==pixel)))
                    print()
                    if param == "toa":
                        variable = toa[(nhits==1)&(row==15)&(col==pixel)] #((nhits==4))] # &(row==15)&(col==pixel))]
                    if param == "tot":
                        variable = tot[(nhits==1)&(row==15)&(col==pixel)] # ((nhits==4))] # &(row==15)&(col==pixel))]
                    variable = variable[np.abs(variable) < 1000]
                    mean_variable = np.mean(variable)
                    std_variable = np.std(variable) / len(variable)
                    if   param == "toa":
                        if np.sum(variable) != 0:
                            mean_toa[pixel].append(mean_variable)
                            print(mean_toa[pixel])
                            std_toa[pixel].append(std_variable)
                        else:
                            mean_toa[pixel].append(0)
                            std_toa[pixel].append(0)
                    elif param == "tot":
                        if np.sum(variable) != 0:
                            mean_tot[pixel].append(mean_variable)
                            print(mean_tot[pixel])
                            std_tot[pixel].append(std_variable)
                        else:
                            mean_tot[pixel].append(0)
                            std_tot[pixel].append(0)
                        # mean_tot[pixel].append(mean_variable)
                        # std_tot[pixel].append(std_variable)
                    elif param == "cal":
                        if np.sum(variable) != 0:
                            mean_cal[pixel].append(mean_variable)
                            print(mean_cal[pixel])
                            std_cal[pixel].append(std_variable)
                        else:
                            mean_cal[pixel].append(0)
                            std_cal[pixel].append(0)
                        # mean_cal[pixel].append(mean_variable)
                        # stc_cal[pixel].append(std_variable)

                    '''
                    print(sum((events["nhits"].array()==4) & ((events_obj["row"]==15)&(events_obj["col"]==pixel))))
                    print(ak.Array([events_obj['bin'][i] * events["toa_code"].array()[i] for i in range(len(events_obj['bin']))]))
                    events_obj['toa'] = 12.5 - array_mult(events_obj['bin'], events["toa_code"].array()) # ak.Array([events_obj['bin'][i] * events["toa_code"].array()[i] for i in range(len(events_obj['bin']))]) # events_obj["bin"] * (events["toa_code"].array())
                    events_obj['tot'] = array_mult((2*(events["tot_code"].array()) - np.floor((events["tot_code"].array())/32)), events_obj["bin"])
                    print(events_obj['bin'], events_obj['toa'])
                    variable = events[param].array()[((events["nhits"].array()==4)&(events_obj["row"]==15)&(events_obj["col"]==pixel))]
                    variable = variable[np.abs(variable) < 100000]
                    if np.abs(np.mean(variable)) == np.inf:
                        print(variable)
                    mean_variable = np.mean(variable)
                    std_variable = np.std(variable) / len(variable)
                    if   param == "toa_code":
                        mean_toa[pixel].append(mean_variable)
                        std_toa[pixel].append(std_variable)
                    elif param == "tot_code":
                        mean_tot[pixel].append(mean_variable)
                        std_tot[pixel].append(std_variable)
                    elif param == "cal_code":
                        mean_cal[pixel].append(mean_variable)
                        stc_cal[pixel].append(std_variable)
                    '''
    a = 10
    fig, ax = plt.subplots(1, len(params), figsize = (a * len(params), a))

    # TOA
    for pixel in pixels:
        print(mean_toa)
        print(intensities)
        print(len(mean_toa[pixel]))
        ax[0].errorbar(intensities, mean_toa[pixel], yerr = std_toa[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o-")
        # print(mean_toa[pixel])
    ax[0].set_ylabel("Mean TOA")
    ax[0].set_xlabel("Threshold DAC values")
    ax[0].legend()

    # TOT
    for pixel in pixels:
        ax[1].errorbar(intensities, mean_tot[pixel], yerr = std_tot[pixel], label = f'Row: 15, Col: {pixel}', fmt = "o-")
        print(mean_tot[pixel])
    ax[1].set_ylabel("Mean TOT")
    ax[1].set_xlabel("Threshold DAC values")
    ax[1].legend()
    plt.show()
    fig.savefig(f"toa_tot_vth_{intensity}.png")
    print()

