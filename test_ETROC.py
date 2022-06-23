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

N_l1a    = 3200 # how many L1As to send
vth_min  =  190 # scan range
vth_max  =  210
vth_step =  .25 # step size
N_steps  = int((vth_max-vth_min)/vth_step)+1 # number of steps
N_pix    =   16 # total number of pixels

# do vth scan
vth_axis    = np.linspace(vth_min, vth_max, N_steps)
run_results = np.empty([N_steps, N_pix])
def sigmoid(k,x,x0): return 1/(1+np.exp(k*(x-x0)))

for vth in vth_axis:
    ETROCobj.set_vth(vth)
    ETROCobj.run(N_l1a);
    i = int((vth-vth_min)/vth_step)
    run_results[i] = ETROCobj.run_results()

# transpose so each 1d list is for a pixel
# also normalize
run_results = run_results.transpose().astype(np.float64)/N_l1a
print(run_results)

# fit to sigmoid
widths = np.empty(N_pix)
means  = np.empty(N_pix)
p0 = [2, 198] # starting guess for fit
for pix in range(N_pix):
    print("for pixel #%d"%pix)
    popt, pcov = curve_fit(sigmoid, vth_axis, run_results[pix], p0, method='dogbox',  maxfev=10000)
    widths[pix] = popt[0] #k
    means[pix] = popt[1] #x0
    print("fit = "+str(popt))
    print(pcov)

# example result and fit
plt.title("S curve test") 
plt.xlabel("Vth") 
plt.ylabel("accumulation number") 
plt.plot(vth_axis, run_results[0])
fit_func = sigmoid(widths[0], vth_axis, means[0])
plt.plot(vth_axis, fit_func)
plt.show()
