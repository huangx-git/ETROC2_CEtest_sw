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
vth_min  =  193 # scan range
vth_max  =  203
vth_step =  .1 # step size
N_steps  = int((vth_max-vth_min)/vth_step)+1 # number of steps
N_pix    =   16 # total number of pixels

# do vth scan
vth_axis    = np.linspace(vth_min, vth_max, N_steps)
run_results = np.empty([N_steps, N_pix])
def sigmoid(k,x,x0): return 1/(1+np.exp(k*(x-x0)))

for vth in vth_axis:
    ETROCobj.set_vth(vth)
    ETROCobj.run(N_l1a);
    i = int(round((vth-vth_min)/vth_step))
    print(i)
    run_results[i] = ETROCobj.run_results()
    print(run_results[i])

# transpose so each 1d list is for a pixel
# also normalize
run_results = run_results.transpose()/N_l1a

# fit to sigmoid
widths = np.empty(N_pix)
means  = np.empty(N_pix)
guess = [2, 5] # starting guess for fit
fitx = vth_axis-vth_min
for pix in range(N_pix):
    print("for pixel #%d"%pix)
    print(run_results[pix])
    popt, pcov = curve_fit(sigmoid, fitx, run_results[pix],  method="trf", bounds=([1,1],[9,5]))
    widths[pix] = popt[0] #k
    means[pix] = popt[1] #x0
    print("fit = "+str(popt))

# example result and fit
plt.title("S curve test") 
plt.xlabel("Vth") 
plt.ylabel("accumulation number") 
plt.plot(fitx, run_results[0])
fit_func = sigmoid(widths[0], fitx, means[0])
plt.plot(fitx, fit_func)
start_func = sigmoid(guess[0], fitx, guess[1])
plt.plot(fitx, start_func)
plt.legend(["data","fit","guess"])
plt.show()
