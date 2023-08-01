#!/usr/bin/env python3
import json
import awkward as ak
import numpy as np
import hist
import matplotlib.pyplot as plt
import mplhep as hep
plt.style.use(hep.style.CMS)

if __name__ == '__main__':

    with open("../output/output_qinj_10fC.json", "r") as f:
        res = json.load(f)
    events = ak.from_json(res)

    events['bin'] = 3.125 / events.cal_code
    events['toa'] = 12.5 - events.bin * events.toa_code
    events['tot'] = (2*events.tot_code - np.floor(events.tot_code/32))*events.bin

    toa = np.nan_to_num(ak.flatten(events.toa), nan=0, posinf=0, neginf=0)
    toa = toa[((toa>7)&(toa<9))]
    toa_mean = np.mean(toa)

    time_axis = hist.axis.Regular(100, toa_mean-2, toa_mean+2, name="time", label="time")
    cal_axis = hist.axis.Regular(2**10, 0, 2**10, name="cal", label="cal")

    toa_hist = hist.Hist(time_axis)
    cal_hist = hist.Hist(cal_axis)
    toa_code_hist = hist.Hist(cal_axis)

    # Making CAL plot
    cal_hist.fill(cal=ak.flatten(events.cal_code))

    fig, ax = plt.subplots()
    cal_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'../results/cal_code.png')

    # Making TOA plots

    toa_code_hist.fill(cal=ak.flatten(events.toa_code))

    fig, ax = plt.subplots()
    toa_code_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'../results/toa_code.png')


    toa_hist.fill(time=ak.flatten(events.toa))

    fig, ax = plt.subplots()
    toa_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'../results/toa.png')


    # there are some nasty outliers that we remove
    # more studies are needed to understand them
    pix_selector = ((events.row==0)&(events.col==0)&(events.cal_code>150)&(events.cal_code<210))
    cal_code_0_0 = events.cal_code[pix_selector]
    bin_0_0 = 3.125/cal_code_0_0
    bin_0_0_avg = np.mean(ak.flatten(bin_0_0))
    toa_0_0 = 12.5 - bin_0_0 * events.toa_code[pix_selector]
    toa_0_0 = toa_0_0[((toa_0_0>7) & (toa_0_0<9))]

    toa_0_0_avg = 12.5 - bin_0_0_avg * events.toa_code[pix_selector]
    toa_0_0_avg = toa_0_0_avg[((toa_0_0_avg>7) & (toa_0_0_avg<9))]

    toa_0_0_mean = np.mean(toa_0_0)
    toa_0_0_std = np.std(toa_0_0)

    toa_0_0_avg_mean = np.mean(toa_0_0_avg)
    toa_0_0_avg_std = np.std(toa_0_0_avg)

    print(f"Found mean time of {round(toa_0_0_avg_mean,3)}fs, with std dev of {round(toa_0_0_avg_std*1000, 0)}ps")

    toa_hist = hist.Hist(time_axis)
    toa_hist.fill(time=ak.flatten(events.toa[((events.row==0)&(events.col==0))]))

    fig, ax = plt.subplots()
    toa_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'../results/toa_0_0.png')
