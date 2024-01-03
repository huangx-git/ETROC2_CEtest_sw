import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
import os
import sys
import pdb

base   = "/home/daq/ETROC2_Test_Stand/ScopeHandler/ScopeData/LecroyMerged"
y_axis = [10623,10626,10627,10630,10631,10632,10635,10636,10637,10638]
x_axis = [185  ,190  ,195  ,200  ,205  ,210  ,215  ,220  ,225  ,230  ]
npixels = 4
a = 10
c = 1.2

def merge_unique(list1, list2):
    merged_list = np.array([(list1[i], list2[i]) for i in range(0, len(list1))])
    if len(merged_list) != 0:
        merged_list = len(np.unique(merged_list, axis = 1))
    else:
        merged_list = len([])
    return merged_list

def get_unique(row, col):
    pairs = ak.Array([merge_unique(row[i], col[i]) for i in range(len(row))])
    return np.array(pairs)

def load_data(indices):
    output = []
    for i, index in enumerate(indices):
        filename = f"{base}/run_{index}.root"
        output.append({})
        with uproot.open(filename) as f:
            tree = f["pulse"]
            output[i]["nhits"]    = tree["nhits"].array()
            tbin                  = 3.125 / tree["cal_code"].array()
            output[i]["TOA"]      = tbin * tree["toa_code"].array()
            output[i]["TOT"]      = (2 * tree["tot_code"].array() - tree["tot_code"].array()) * tbin
            output[i]["CAL"]      = tree["cal_code"].array()
            output[i]["row"]      = tree["row"].array()
            output[i]["col"]      = tree["col"].array()
            output[i]["LP2_20_6"] = tree["LP2_20"].array()[:, 6]
            output[i]["LP2_20_7"] = tree["LP2_20"].array()[:, 7]
            print(filename)
    return output

def plots(data, x_axis):
    mean_toa = [[] for i in range(npixels)]
    mean_tot = [[] for i in range(npixels)]
    mean_cal = [[] for i in range(npixels)]
    std_toa  = [[] for i in range(npixels)]
    std_tot  = [[] for i in range(npixels)]
    std_cal  = [[] for i in range(npixels)]
    mean_DT  = [[] for i in range(npixels)]
    std_DT   = [[] for i in range(npixels)]
    for d in data:
        sel = ((d["nhits"] == npixels) & (get_unique(d["row"], d["col"]) == npixels))
        row = d["row"][sel]
        col = d["col"][sel]
        for p in range(npixels):
            pixel_sel = ((row == 15) & (col == p))
            print(d["TOA"][sel][pixel_sel])
            try:
                toa = np.reshape(d["TOA"][sel][pixel_sel], len(d["TOA"][sel][pixel_sel]))
            except:
                pdb.set_trace()
            tot = np.reshape(d["TOT"][sel][pixel_sel], len(d["TOT"][sel][pixel_sel]))
            cal = np.reshape(d["CAL"][sel][pixel_sel], len(d["CAL"][sel][pixel_sel]))
            LP2_20_6 = d["LP2_20_6"][sel][np.any(pixel_sel, axis = 1)]
            LP2_20_7 = d["LP2_20_7"][sel][np.any(pixel_sel, axis = 1)]
            mean_toa[p].append(np.mean(toa))
            mean_tot[p].append(np.mean(tot))
            mean_cal[p].append(np.mean(cal))
            std_toa [p].append(np.std (toa))
            std_tot [p].append(np.std (tot))
            std_cal [p].append(np.std (cal))
            mean_DT [p].append(np.mean(toa - (LP2_20_7 - LP2_20_6)*10**9))
            std_DT  [p].append(np.std (toa - (LP2_20_7 - LP2_20_6)*10**9))
    variables = [mean_toa, mean_tot, mean_cal, std_toa, std_tot, std_cal, mean_DT, std_DT]
    labels    = ["mean_toa", "mean_tot", "mean_cal", "std_toa", "std_tot", "std_cal", "mean_DT", "std_DT"]
    vars      = zip(labels, variables)
    for v, var in enumerate(variables):
        fig, ax = plt.subplots(1, 1, figsize = (1*a*c, 1*a))
        for p in range(npixels):
            if "mean" in labels[v]:
                ax.errorbars(x_axis, var, yerr = vars["std" + lables[v].split("mean")[1]])
            else:
                ax.scatter(x_axis, var)
            ax.plot(x_axis, var)
        fig.savefig(f"{labels[v]}.png")

if __name__ == "__main__":
    data = load_data(y_axis)
    plots(data, x_axis)