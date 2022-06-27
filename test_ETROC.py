from tamalero.ETROC import ETROC
from ETROC_Emulator import I2C_write, I2C_read

import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt

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

# ==== CONSTANTS ====
N_l1a    = 3200 # how many L1As to send
vth_min  =  193 # scan range
vth_max  =  203
vth_step =  .25 # step size
N_steps  = int((vth_max-vth_min)/vth_step)+1 # number of steps
N_pix    =   16 # total number of pixels
N_pix_w  =    4 # N where pixels are in NxN layout

# ===== HELPERS =====
polyfit = np.polynomial.polynomial.polyfit

def sigmoid(k,x,x0):
    return 1/(1+np.exp(k*(x-x0)))

# change y = 1 / (1 + e^(-k(x-x0))) to log(1/y - 1) = -k(x-x0)
def sigmoid_log(ylist):
    fity = []
    for y in ylist:
        if abs(y) <= 0.001:
            fity.append(np.inf)
        else:
            fity.append(np.log(1/y - 1))
    return np.array(fity)

# take x,y values and perform fit to sigmoid function
# return width(k) and mean(x0)
def sigmoid_fit(x_axis,y_axis):
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

# ===== Vth scan ====
vth_axis    = np.linspace(vth_min, vth_max, N_steps)
run_results = np.empty([N_steps, N_pix])

for vth in vth_axis:
    ETROCobj.set_vth(vth)
    ETROCobj.run(N_l1a);
    i = int(round((vth-vth_min)/vth_step))
    run_results[i] = ETROCobj.run_results()

# transpose so each 1d list is for a pixel
# also normalize
run_results = run_results.transpose()/N_l1a

# fit to sigmoid
widths = np.empty([N_pix_w, N_pix_w])
means  = np.empty([N_pix_w, N_pix_w])
#widths = np.empty(N_pix)
#means  = np.empty(N_pix)

for pix in range(N_pix):
    print("for pixel #%d"%pix)
    fitresults = sigmoid_fit(vth_axis, run_results[pix])
    print(fitresults)
    r = pix%N_pix_w
    c = int(np.floor(pix/N_pix_w))
    print("row = %d, col = %d"%(r,c))
    widths[r][c] = fitresults[0]
    means[r][c]  = fitresults[1]

    #popt, pcov = curve_fit(sigmoid, fitx, run_results[pix],  method="trf", bounds=([1,1],[9,5]))
    #widths[pix] = popt[0] #k
    #means[pix] = popt[1] #x0
    #print("fit = "+str(popt))

# example fit result
plt.title("S curve fit example (pixel #0)") 
plt.xlabel("Vth") 
plt.ylabel("hit percentage") 
plt.plot(vth_axis, run_results[0])
fit_func = sigmoid(widths[0][0], vth_axis, means[0][0])
plt.plot(vth_axis, fit_func)
plt.legend(["data","fit"])

# 2D histogram

plt.title("Mean values of baseline voltage")
plt.matshow(widths)
plt.show()
