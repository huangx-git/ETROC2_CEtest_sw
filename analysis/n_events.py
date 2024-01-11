import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import sys
import pdb

base   = "/home/daq/ETROC2_Test_Stand/ScopeHandler/ScopeData/LecroyMerged"
output_folder = "/home/daq/ETROC2_Test_Stand/module_test_sw/analysis/plots"
# y_axis = [10623,10626,10627,10630,10631,10632,10635,10636,10637,10638]
# x_axis = [185  ,190  ,195  ,200  ,205  ,210  ,215  ,220  ,225  ,230  ]
# npixels = 4

y_axis = [10643,10644,10647,10651,10652,10653,10654,10655,10656,10657,10658,10660,10661,10662,10663,10664]
x_axis = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
# y_axis = [10668]
# x_axis = [3]
npixels = 4
a = 8
c = 1

def merge_unique(list1, list2):
    merged_list = [(list1[i], list2[i]) for i in range(0, len(list1))]
    if len(merged_list) != 0:
        merged_list = len(set(merged_list))
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
            output[i]["LP2_30_6"] = tree["LP2_30"].array()[:, 6]
            output[i]["LP2_35_6"] = tree["LP2_35"].array()[:, 6]
            output[i]["LP2_40_6"] = tree["LP2_40"].array()[:, 6]
            output[i]["LP2_50_6"] = tree["LP2_50"].array()[:, 6]
            output[i]["LP2_60_6"] = tree["LP2_60"].array()[:, 6]
            output[i]["LP2_70_6"] = tree["LP2_70"].array()[:, 6]
            output[i]["LP2_80_6"] = tree["LP2_80"].array()[:, 6]
            output[i]["LP2_20_7"] = tree["LP2_20"].array()[:, 7]
            output[i]["LP2_30_7"] = tree["LP2_30"].array()[:, 7]
            output[i]["LP2_35_7"] = tree["LP2_35"].array()[:, 7]
            output[i]["LP2_40_7"] = tree["LP2_40"].array()[:, 7]
            output[i]["LP2_50_7"] = tree["LP2_50"].array()[:, 7]
            output[i]["LP2_60_7"] = tree["LP2_60"].array()[:, 7]
            output[i]["LP2_70_7"] = tree["LP2_70"].array()[:, 7]
            output[i]["LP2_80_7"] = tree["LP2_80"].array()[:, 7]
            # print(filename)
    return output

def remove_empty(data):
    map = ak.count(data, axis = -1) > 0 # np.array().astype(bool)
    data = data[map]
    return data

def rescale(elem):
    # print(elem)
    if elem < 0:
        elem = elem - 25 * np.floor(elem / 25)
    elif elem > 25:
        print(elem)
        elem = elem - 25 * np.ceil(elem / 25)
        print(elem * np.ceil(elem / 25))
        print(elem)
        print()
    return elem

def scan(data): # a dictionary
    print(list(data.keys()))
    print(len(data[list(data.keys())[0]]), len(data[list(data.keys())[1]]), len(data[list(data.keys())[2]]))
    maximum = max([len(data[list(data.keys())[0]]), len(data[list(data.keys())[1]]), len(data[list(data.keys())[2]])])
    if not (len(data[list(data.keys())[0]]) == len(data[list(data.keys())[1]]) == len(data[list(data.keys())[2]])):
        for i in range(maximum):
            for j in data.keys():
                print(data[j][i], end = ",")
            print()

def plots(data, x_axis):
    mean_toa = [[] for i in range(npixels)]
    mean_tot = [[] for i in range(npixels)]
    mean_cal = [[] for i in range(npixels)]
    std_toa  = [[] for i in range(npixels)]
    std_tot  = [[] for i in range(npixels)]
    std_cal  = [[] for i in range(npixels)]
    std_clock   = [[] for i in range(npixels)]
    std_trigger = [[] for i in range(npixels)]
    mean_DT  = [[] for i in range(npixels)]
    std_DT   = [[] for i in range(npixels)]
    TOA      = [[] for i in range(npixels)]
    TOT      = [[] for i in range(npixels)]
    CAL      = [[] for i in range(npixels)]
    DT       = [[] for i in range(npixels)]
    hits     = []
    LP2_20_6_= [[] for i in range(len(x_axis))]
    LP2_30_6_= [[] for i in range(len(x_axis))]
    LP2_35_6_= [[] for i in range(len(x_axis))]
    LP2_40_6_= [[] for i in range(len(x_axis))]
    LP2_50_6_= [[] for i in range(len(x_axis))]
    LP2_60_6_= [[] for i in range(len(x_axis))]
    LP2_70_6_= [[] for i in range(len(x_axis))]
    LP2_80_6_= [[] for i in range(len(x_axis))]
    LP2_20_7_= [[] for i in range(len(x_axis))]
    LP2_30_7_= [[] for i in range(len(x_axis))]
    LP2_35_7_= [[] for i in range(len(x_axis))]
    LP2_40_7_= [[] for i in range(len(x_axis))]
    LP2_50_7_= [[] for i in range(len(x_axis))]
    LP2_60_7_= [[] for i in range(len(x_axis))]
    LP2_70_7_= [[] for i in range(len(x_axis))]
    LP2_80_7_= [[] for i in range(len(x_axis))]
    for d_i, d in enumerate(data):
        sel = ((d["nhits"] == npixels) & (get_unique(d["row"], d["col"]) == npixels))
        row = d["row"][sel]
        col = d["col"][sel]
        toa = d["TOA"][sel]
        tot = d["TOT"][sel]
        cal = d["CAL"][sel]
        LP2_20_6 = d["LP2_20_6"][sel]*10**9
        LP2_30_6 = d["LP2_30_6"][sel]*10**9
        LP2_35_6 = d["LP2_35_6"][sel]*10**9
        LP2_40_6 = d["LP2_40_6"][sel]*10**9
        LP2_50_6 = d["LP2_50_6"][sel]*10**9
        LP2_60_6 = d["LP2_60_6"][sel]*10**9
        LP2_70_6 = d["LP2_70_6"][sel]*10**9
        LP2_80_6 = d["LP2_80_6"][sel]*10**9
        LP2_20_7 = d["LP2_20_7"][sel]*10**9
        LP2_30_7 = d["LP2_30_7"][sel]*10**9
        LP2_35_7 = d["LP2_35_7"][sel]*10**9
        LP2_40_7 = d["LP2_40_7"][sel]*10**9
        LP2_50_7 = d["LP2_50_7"][sel]*10**9
        LP2_60_7 = d["LP2_60_7"][sel]*10**9
        LP2_70_7 = d["LP2_70_7"][sel]*10**9
        LP2_80_7 = d["LP2_80_7"][sel]*10**9
        LP2_20_6 = np.array([rescale(i) for i in LP2_20_6])
        LP2_30_6 = np.array([rescale(i) for i in LP2_30_6])
        LP2_35_6 = np.array([rescale(i) for i in LP2_35_6])
        LP2_40_6 = np.array([rescale(i) for i in LP2_40_6])
        LP2_50_6 = np.array([rescale(i) for i in LP2_50_6])
        LP2_60_6 = np.array([rescale(i) for i in LP2_60_6])
        LP2_70_6 = np.array([rescale(i) for i in LP2_70_6])
        LP2_80_6 = np.array([rescale(i) for i in LP2_80_6])
        hits.append(d["nhits"])
        for p in range(npixels):
            pixel_sel = ((row == 15) & (col == p)) # element level selection
            print("===========================> ", p)
            toa_ = toa[pixel_sel]
            tot_ = tot[pixel_sel]
            cal_ = cal[pixel_sel]
            # try:
            #     assert (len(cal_) == len(toa_) == len(tot_))
            # except:
            #     obj = {"TOA": toa_, "TOT": tot_, "CAL": cal_}
            #     scan(obj)
            obj = {"TOA": toa_, "TOT": tot_, "CAL": cal_}
            element_sel = ((cal_ > 195) & (cal_ < 210) & (tot_ > 1.0) & (tot_ < 1.5)) # ((cal_ > 195) & (cal_ < 210) & (tot_ > 1.0) & (tot_ < 1.5))
            event_sel   = (np.any(element_sel, axis = 1) & (LP2_20_6 > 0))
            toa_ = toa_[element_sel][event_sel]
            tot_ = tot_[element_sel][event_sel]
            cal_ = cal_[element_sel][event_sel]
            # toa_ = remove_empty(toa_)
            # tot_ = remove_empty(tot_)
            # cal_ = remove_empty(cal_)
            # scan(obj)
            toa_ = toa_[:,0] # np.reshape(toa_, len(toa_))
            tot_ = tot_[:,0] # np.reshape(tot_, len(tot_))
            cal_ = cal_[:,0] # np.reshape(cal_, len(cal_))
            print(len(cal_), len(toa_), len(tot_))
            LP2_20_6_[d_i] = LP2_20_6[event_sel]
            LP2_30_6_[d_i] = LP2_30_6[event_sel]
            LP2_35_6_[d_i] = LP2_35_6[event_sel]
            LP2_40_6_[d_i] = LP2_40_6[event_sel]
            LP2_50_6_[d_i] = LP2_50_6[event_sel]
            LP2_60_6_[d_i] = LP2_60_6[event_sel]
            LP2_70_6_[d_i] = LP2_70_6[event_sel]
            LP2_80_6_[d_i] = LP2_80_6[event_sel]
            LP2_20_7_[d_i] = LP2_20_7[event_sel]
            LP2_30_7_[d_i] = LP2_30_7[event_sel]
            LP2_35_7_[d_i] = LP2_35_7[event_sel]
            LP2_40_7_[d_i] = LP2_40_7[event_sel]
            LP2_50_7_[d_i] = LP2_50_7[event_sel]
            LP2_60_7_[d_i] = LP2_60_7[event_sel]
            LP2_70_7_[d_i] = LP2_70_7[event_sel]
            LP2_80_7_[d_i] = LP2_80_7[event_sel]
            mean_toa[p].append(np.mean(toa_))
            mean_tot[p].append(np.mean(tot_))
            mean_cal[p].append(np.mean(cal_))
            TOA     [p].append(toa_)
            TOT     [p].append(tot_)
            CAL     [p].append(cal_)
            std_toa [p].append(np.std (toa_))
            std_tot [p].append(np.std (tot_))
            std_cal [p].append(np.std (cal_))
            std_clock  [p].append(np.std (LP2_20_6_[d_i]))
            std_trigger[p].append(np.std (LP2_20_7_[d_i]))
            DT      [p].append(toa_ - (LP2_20_7_[d_i] - LP2_20_6_[d_i]))
            mean_DT [p].append(np.mean(DT[p][d_i]))
            std_DT  [p].append(np.std (DT[p][d_i]))

    variables = [mean_toa, mean_tot, mean_cal, std_toa, std_tot, std_cal, std_clock, std_trigger, mean_DT, std_DT]
    variables = [np.nan_to_num(var) for var in variables]
    labels    = ["mean_toa", "mean_tot", "mean_cal", "std_toa", "std_tot", "std_cal", "std_clock", "std_trigger", "mean_DT", "std_DT"]
    vars      = dict(zip(labels, variables))
    for v, var in enumerate(variables):
        print(labels[v])
        fig, ax = plt.subplots(1, 1, figsize = (1*a*c, 1*a))
        for p in range(npixels):
            print(f"Pixel: {p}")
            var = np.array(var)
            var[var==np.inf] = 0
            print(x_axis, var[p])
            if "mean" in labels[v]:
                ax.errorbar(x_axis, var[p], yerr = vars["std" + labels[v].split("mean")[1]][p], label = f"Row: 15, Col: {p}", fmt = "o", capsize = 10)
            else:
                ax.scatter(x_axis, var[p], label = f"Row: 15, Col: {p}")
            ax.plot(x_axis, var[p])
        ax.set_xlabel("Bias voltage [V]")
        ax.set_ylabel(labels[v])
        ax.legend()
        fig.savefig(f"{output_folder}/{labels[v]}.png")

    variables = [TOA  ,  TOT ,  CAL , \
                 LP2_20_6_ ,  LP2_30_6_ ,  LP2_35_6_ ,  LP2_40_6_ , LP2_50_6_  ,  LP2_60_6_ ,  LP2_70_6_ ,  LP2_80_6_ , \
                 LP2_20_7_ ,  LP2_30_7_ ,  LP2_35_7_ ,  LP2_40_7_ , LP2_50_7_  ,  LP2_60_7_ ,  LP2_70_7_ ,  LP2_80_7_ ,  hits , DT  ]

    labels    = ["TOA", "TOT", "CAL", \
                 "LP2_20_6_", "LP2_30_6_", "LP2_35_6_", "LP2_40_6_", "LP2_50_6_", "LP2_60_6_", "LP2_70_6_", "LP2_80_6_", \
                 "LP2_20_7_", "LP2_30_7_", "LP2_35_7_", "LP2_40_7_", "LP2_50_7_", "LP2_60_7_", "LP2_70_7_", "LP2_80_7_", "hits", "DT"]

    vars      = dict(zip(labels, variables))

    for v, var in enumerate(variables):
        if labels[v] == "TOA" or labels[v] == "TOT" or labels[v] == "CAL" or labels[v] == "DT":
            print("--------------------------- ", labels[v])
            minimum = min([min([min(var[p][i]) if len(var[p][i]) != 0 else 10000 for p in range(npixels)]) for i in range(len(x_axis))])
            maximum = max([max([max(var[p][i]) if len(var[p][i]) != 0 else 0     for p in range(npixels)]) for i in range(len(x_axis))])
            for p in range(npixels):
                fig, ax = plt.subplots(1, 1, figsize = (1*a*c, 1*a))
                for j in range(len(x_axis)):
                    # if not (x_axis[j] in [185, 195, 205, 215]): continue
                    if not (x_axis[j] in [3,4,5,6,7]): continue
                    # print(var[p])
                    bins = np.linspace(minimum, maximum, 15)
                    weights = np.ones(len(var[p][j])) / len(var[p][j])
                    print(len(weights))
                    ax.hist(var[p][j], label = f"Bias voltage: {x_axis[j]} V", bins = bins, histtype = "step") # , weights = weights)
                ax.set_xlabel(labels[v])
                ax.set_ylabel("Events")
                ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useOffset=False))
                handles, label = ax.get_legend_handles_labels()
                idx = np.sort(np.unique(np.array(label), return_index=True)[1])
                ax.legend(np.array(label)[idx])
                fig.savefig(f"{output_folder}/{labels[v]}_PIXEL_15_{p}_HIST.png")
        else:
            fig, ax = plt.subplots(1, 1, figsize = (1*a*c, 1*a))
            print("--------------------------- ", labels[v])
            minimum = min([min(var[i]) if len(var[i]) != 0 else 10000 for i in range(len(x_axis))])
            maximum = max([max(var[i]) if len(var[i]) != 0 else 0     for i in range(len(x_axis))])
            for j in range(len(x_axis)):
                if not (x_axis[j] in [3,4,5,6,7]): continue # [0,1,2,3,7,10,15]
                bins = np.linspace(minimum, maximum, 20)
                weights = np.ones(len(var[j])) / len(var[j])
                ax.hist(var[j], label = f"Bias voltage: {x_axis[j]} V", bins = bins, histtype = "step") # , weights = weights)
            ax.set_xlabel(labels[v])
            ax.set_ylabel("Events")
            handles, label = ax.get_legend_handles_labels()
            idx = np.sort(np.unique(np.array(label), return_index=True)[1])
            ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useOffset=False))
            ax.legend(np.array(label)[idx])
            fig.savefig(f"{output_folder}/{labels[v]}_HIST.png")
    for i in range(len(x_axis)): # toa vs tot
        fig, ax = plt.subplots(2, 2, figsize = (2*a*c, 2*a))
        for p in range(npixels):
            x = int(np.floor(p / 2))
            y = int(p % 2)
            print(x, y)
            # bins = np.linspace(minimum, maximum, 15)
            # weights = np.ones(len(var[p][j])) / len(var[p][j])
            print(len(variables[0][p][i]), len(variables[1][p][i]))
            ax[x][y].hist2d(np.array(variables[0][p][i]), np.array(variables[1][p][i]), bins = (50, 50)) #, cmap=plt.cm.jet) # , histtype = "step" weights = weights)
            ax[x][y].set_title(f"Row: 15, Col: {p}")
            ax[x][y].set_xlabel("TOA")
            ax[x][y].set_ylabel("TOT")
            ax[x][y].xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useOffset=False))
        fig.savefig(f"{output_folder}/TOA_vs_TOT_row_15_col_{p}_{x_axis[i]}.png")

    for i in range(len(x_axis)): # toa vs cal
        fig, ax = plt.subplots(2, 2, figsize = (2*a*c, 2*a))
        for p in range(npixels):
            x = int(np.floor(p / 2))
            y = int(p % 2)
            print(x, y)
            # bins = np.linspace(minimum, maximum, 15)
            # weights = np.ones(len(var[p][j])) / len(var[p][j])
            print(len(variables[0][p][i]), len(variables[2][p][i]))
            ax[x][y].hist2d(np.array(variables[0][p][i]), np.array(variables[2][p][i]), bins = (50, 50)) #, cmap=plt.cm.jet) # , histtype = "step" weights = weights)
            ax[x][y].set_title(f"Row: 15, Col: {p}")
            ax[x][y].set_xlabel("TOA")
            ax[x][y].set_ylabel("CAL")
            ax[x][y].xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useOffset=False))
        fig.savefig(f"{output_folder}/TOA_vs_CAL_row_15_col_{p}_{x_axis[i]}.png")

    '''
    for i in range(len(x_axis)): # toa vs DT
        fig, ax = plt.subplots(2, 2, figsize = (2*a*c, 2*a))
        for p in range(npixels):
            x = int(np.floor(p / 2))
            y = int(p % 2)
            print(x, y)
            # bins = np.linspace(minimum, maximum, 15)
            # weights = np.ones(len(var[p][j])) / len(var[p][j])
            print(len(variables[0][p][i]), len(variables[13][p][i]))
            ax[x][y].hist2d(np.array(variables[0][p][i]), np.array(variables[13][p][i]), bins = (50, 50)) #, cmap=plt.cm.jet) # , histtype = "step" weights = weights)
            ax[x][y].set_title(f"Row: 15, Col: {p}")
            ax[x][y].set_xlabel("TOA")
            ax[x][y].set_ylabel("DT")
            ax[x][y].xaxis.set_major_formatter(mpl.ticker.ScalarFormatter(useOffset=False))
        fig.savefig(f"{output_folder}/TOA_vs_DT_row_15_col_{p}_{x_axis[i]}.png")
    '''

if __name__ == "__main__":
    data = load_data(y_axis)
    plots(data, x_axis)
