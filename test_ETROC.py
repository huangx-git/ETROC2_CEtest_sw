from tamalero.ETROC import ETROC
from ETROC_Emulator import I2C_write, I2C_read, init_bl

import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt

import os
import json

ETROCobj = ETROC(I2C_write, I2C_read)

# ==============================
# === Test simple read/write ===
# ==============================

print("Test simple read/write...")
ETROCobj.test_write(0x0, 42)
print("Write 42 to test register")
testval = ETROCobj.test_read(0x0)
print("Reading test register...%d"%testval)
if testval == 42: print("Read/write successful\n")
else: print("Something's wrong\n")

# ==============================
# ======= Test Vth scan ========
# ==============================

print("Testing Vth scan...")

# ===== HELPERS =====
polyfit = np.polynomial.polynomial.polyfit

def sigmoid(k,x,x0):
    return 1/(1+np.exp(k*(x-x0)))

# change y = 1 / (1 + e^(-k(x-x0))) to log(1/y - 1) = -k(x-x0)
def sigmoid_log(ylist):
    fity = []
    for y in ylist:
        if abs(y) <= 0.01:
            fity.append(np.inf)
        else:
            fity.append(np.log(1/y - 1))
    return np.array(fity)

def sigmoid_fit(x_axis, y_axis):
    res = curve_fit(
        #sigmoid,
        lambda x,a,b: 1/(1+np.exp(a*(x-b))),  # for whatever reason this fit only works with a lambda function?
        x_axis-x_axis[0],
        y_axis,
        maxfev=10000,
    )
    return res[0][0], res[0][1]+x_axis[0]

# take x,y values and perform fit to sigmoid function
# return steepness(k) and mean(x0)
def sigmoid_fit_log(x_axis,y_axis):
    y_axis = sigmoid_log(y_axis)
    x_axis_fit = []
    y_axis_fit = []
    for i in range(x_axis.size):
        # only keep values within linearly shaped range
        if abs(y_axis[i]) < 3:
            x_axis_fit.append(x_axis[i])
            y_axis_fit.append(y_axis[i])
    results = polyfit(x_axis_fit, y_axis_fit, 1)
    kx0, k = results[0], results[1]
    x0 = - kx0 / k
    return (k, x0)

def vth_scan():
    N_l1a    = 3200 # how many L1As to send
    vth_min  =  190 # scan range
    vth_max  =  208
    vth_step =  .25 # step size
    N_steps  = int((vth_max-vth_min)/vth_step)+1 # number of steps
    N_pix    =  256 # total number of pixels
    
    vth_axis    = np.linspace(vth_min, vth_max, N_steps)
    run_results = np.empty([N_steps, N_pix])

    for vth in vth_axis:
        ETROCobj.set_vth(vth)
        ETROCobj.run(N_l1a);
        i = int(round((vth-vth_min)/vth_step))
        run_results[i] = ETROCobj.run_results()

    # transpose so each 1d list is for a pixel & normalize
    run_results = run_results.transpose()/N_l1a
    return [vth_axis.tolist(), run_results.tolist()]

# ===== Vth scan ====

# run only if no saved data
if not os.path.isfile("vth_scan_results.json"):
    print("No data. Run new vth scan...")
    init_bl()
    result_data = vth_scan()
    with open("vth_scan_results.json", "w") as outfile:
        json.dump(result_data, outfile)
        print("New data saved to vth_scan_results.json\n")

# read data
with open('vth_scan_results.json', 'r') as openfile:
    vth_scan_data = json.load(openfile)

vth_axis = np.array(vth_scan_data[0])
hit_rate = np.array(vth_scan_data[1])

vth_min = vth_axis[0]  # vth scan range
vth_max = vth_axis[-1]
N_pix   = len(hit_rate) # total # of pixels
N_pix_w = int(round(np.sqrt(N_pix))) # N_pix in NxN layout

# fit to sigmoid and save to NxN layout
slopes = np.empty([N_pix_w, N_pix_w])
means  = np.empty([N_pix_w, N_pix_w])
widths = np.empty([N_pix_w, N_pix_w])

for pix in range(N_pix):
    fitresults = sigmoid_fit(vth_axis, hit_rate[pix])
    r = pix%N_pix_w
    c = int(np.floor(pix/N_pix_w))
    slopes[r][c] = fitresults[0]
    means[r][c]  = fitresults[1]
    widths[r][c] = 4/fitresults[0]

# print out results nicely
for r in range(N_pix_w):
    for c in range(N_pix_w):
        pix = c*16+r
        print("{:8s}".format("#"+str(pix)), end='')
    print("")
    for c in range(N_pix_w):
        print("%4.2f"%means[r][c], end='  ')
    print("")
    for c in range(N_pix_w):
        print("+-%2.2f"%widths[r][c], end='  ')
    print("\n")

# example fit result
#
if not os.path.isdir('results'):
    os.makedirs('results')

for expix in range(256):
    #expix = 2 # which pixel?
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
    del fig

# 2D histogram
fig2, ax2 = plt.subplots()
plt.title("Mean values of baseline voltage")
cax = ax2.matshow(means)

fig2.colorbar(cax)
ax2.set_xticks(np.arange(N_pix_w))
ax2.set_yticks(np.arange(N_pix_w))

#for i in range(N_pix_w):
#    for j in range(N_pix_w):
#        text = ax2.text(j, i, round(slopes[i, j],2),
#                       ha="center", va="center", color="w")

plt.show()
