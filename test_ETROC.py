from tamalero.ETROC import ETROC
from ETROC_Emulator import software_ETROC2
from tamalero.DataFrame import DataFrame

import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt

import os
import json


# initiate
ETROC2 = ETROC(usefake=True)
DF = DataFrame('ETROC2')

# argsparser
import argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--rerun', action='store_true', default=False, help="Rerun Vth scan and overwrite data?")
argParser.add_argument('--nofitplots', action='store_true', default=False, help="Don't create individual fit plots for all pixels?")
args = argParser.parse_args()


# ==============================
# === Test simple read/write ===
# ==============================

print("<--- Test simple read/write --->")

ETROC2.write(0x0, 42)

print("Write 42 to test register")
testval = ETROC2.read(0x0)

print("Reading test register...%d"%testval)
if testval == 42: print("Read/write successful\n")
else: print("Something's wrong\n")


# ==============================
# ======= Test Vth scan ========
# ==============================

print("<--- Testing Vth scan --->")


# ====== HELPER FUNCTIONS ======

# run N L1A's and return packaged ETROC2 dataformat
def run(N):
    # currently uses the software ETROC to produce fake data
    return ETROC2.fakeETROC.run(N)


def toPixNum(row, col, w):
    return col*w+row


def fromPixNum(pix, w):
    row = pix%w
    col = int(np.floor(pix/w))
    return row, col


def sigmoid(k,x,x0):
    return 1/(1+np.exp(k*(x-x0)))


# take x,y values and perform fit to sigmoid function
# return steepness(k) and mean(x0)
def sigmoid_fit(x_axis, y_axis):
    res = curve_fit(
        #sigmoid,
        lambda x,a,b: 1/(1+np.exp(a*(x-b))),  # for whatever reason this fit only works with a lambda function?
        x_axis-x_axis[0],
        y_axis,
        maxfev=10000,
    )
    return res[0][0], res[0][1]+x_axis[0]


# parse ETROC dataformat into 1D list of # of hits per pixel
def parse_data(data, N_pix):
    results = np.zeros(N_pix)
    pix_w = int(round(np.sqrt(N_pix)))
    
    for word in data:
        datatype, res = DF.read(word)
        if datatype == 'data':
            pix = toPixNum(res['row_id'], res['col_id'], pix_w)
            results[pix] += 1
 
    return results


def vth_scan(ETROC2):
    N_l1a    = 3200 # how many L1As to send
    vth_min  =  190 # scan range
    vth_max  =  210
    vth_step =  .25 # step size
    N_steps  = int((vth_max-vth_min)/vth_step)+1 # number of steps
    N_pix    =  256 # total number of pixels
    
    vth_axis    = np.linspace(vth_min, vth_max, N_steps)
    run_results = np.empty([N_steps, N_pix])

    for vth in vth_axis:
        ETROC2.set_vth(vth)
        i = int(round((vth-vth_min)/vth_step))
        run_results[i] = parse_data(run(N_l1a), N_pix)
    
    # transpose so each 1d list is for a pixel & normalize
    run_results = run_results.transpose()/N_l1a
    return [vth_axis.tolist(), run_results.tolist()]


# ========= Vth SCAN =========

# run can only if no saved data or we want to rerun
if (not os.path.isfile("results/vth_scan.json")) or args.rerun:
    
    print("No data. Run new vth scan...")
    
    result_data = vth_scan(ETROC2)
    
    if not os.path.isdir('results'):
        os.makedirs('results')
    
    with open("results/vth_scan.json", "w") as outfile:
        json.dump(result_data, outfile)
        print("Data saved to results/vth_scan.json\n")


# read data
with open('results/vth_scan.json', 'r') as openfile:
    vth_scan_data = json.load(openfile)

vth_axis = np.array(vth_scan_data[0])
hit_rate = np.array(vth_scan_data[1])

vth_min = vth_axis[0]  # vth scan range
vth_max = vth_axis[-1]
N_pix   = len(hit_rate) # total # of pixels
N_pix_w = int(round(np.sqrt(N_pix))) # N_pix in NxN layout


# ======= PERFORM FITS =======

# fit to sigmoid and save to NxN layout
slopes = np.empty([N_pix_w, N_pix_w])
means  = np.empty([N_pix_w, N_pix_w])
widths = np.empty([N_pix_w, N_pix_w])

for pix in range(N_pix):
    fitresults = sigmoid_fit(vth_axis, hit_rate[pix])
    r, c = fromPixNum(pix, N_pix_w)
    slopes[r][c] = fitresults[0]
    means[r][c]  = fitresults[1]
    widths[r][c] = 4/fitresults[0]

# print out results nicely
for r in range(N_pix_w):
    for c in range(N_pix_w):
        pix = toPixNum(r, c, N_pix_w)
        print("{:8s}".format("#"+str(pix)), end='')
    print("")
    for c in range(N_pix_w):
        print("%4.2f"%means[r][c], end='  ')
    print("")
    for c in range(N_pix_w):
        print("+-%2.2f"%widths[r][c], end='  ')
    print("\n")


# ======= PLOT RESULTS =======

# fit results per pixel & save
if not args.nofitplots:
    print('Creating plots and saving in ./results/...')
    print('This may take a while.')
    for expix in range(256):
        exr   = expix%N_pix_w
        exc   = int(np.floor(expix/N_pix_w))

        fig, ax = plt.subplots()

        plt.title("S curve fit example (pixel #%d)"%expix)
        plt.xlabel("Vth")
        plt.ylabel("hit rate")

        plt.plot(vth_axis, hit_rate[expix], '.-')
        fit_func = sigmoid(slopes[exr][exc], vth_axis, means[exr][exc])
        plt.plot(vth_axis, fit_func)
        plt.axvline(x=means[exr][exc], color='r', linestyle='--')
        plt.axvspan(means[exr][exc]-widths[exr][exc], means[exr][exc]+widths[exr][exc],
                    color='r', alpha=0.1)

        plt.xlim(vth_min, vth_max)
        plt.grid(True)
        plt.legend(["data","fit","baseline"])

        fig.savefig(f'results/pixel_{expix}.png')
        plt.close(fig)
        del fig, ax

# 2D histogram of the mean
fig, ax = plt.subplots()
plt.title("Mean values of baseline voltage")
cax = ax.matshow(means)

fig.colorbar(cax)
ax.set_xticks(np.arange(N_pix_w))
ax.set_yticks(np.arange(N_pix_w))

for i in range(N_pix_w):
    for j in range(N_pix_w):
        text = ax.text(j, i, "%.2f\n+/-%.2f"%(means[i,j],widths[i,j]),
                ha="center", va="center", color="w", fontsize="xx-small")

fig.savefig(f'results/sigmoid_mean_2D.png')
plt.show()

plt.close(fig)
del fig, ax

# 2D histogram of the width
fig, ax = plt.subplots()
plt.title("Width of the sigmoid")
cax = ax.matshow(
    widths,
    cmap='RdYlGn_r',
    vmin=0, vmax=5,
)

fig.colorbar(cax)
ax.set_xticks(np.arange(N_pix_w))
ax.set_yticks(np.arange(N_pix_w))

#cax.set_zlim(0, 10)

fig.savefig(f'results/sigmoid_width_2D.png')
plt.show()
