from tamalero.ETROC import ETROC
from ETROC_Emulator import I2C_write, I2C_read

import numpy as np
from matplotlib import pyplot as plt

ETROCobj = ETROC(I2C_write, I2C_read)

# ========= Test simple read/write =========
print("Test simple read/write...")
ETROCobj.test_write(0x0, 1)
testval = ETROCobj.test_read(0x0)
print(testval)
print("")

# ============ Test Vth S curve ============
N = 3200
vth_min, vth_max = 190, 210
vth_step = 1
testpixel = 10
print("Testing Vth S curve scan for pixel #%d..."%testpixel)

vth_axis = np.arange(vth_min, vth_max, vth_step)
acc_num_axis = np.zeros(vth_axis.size)

for vth in range(vth_min, vth_max, vth_step):
    ETROCobj.set_vth(vth)
    ETROCobj.run(N);
    i = int((vth-vth_min)/vth_step)
    acc_num_axis[i] = ETROCobj.run_results()[testpixel]

plt.title("S curve test") 
plt.xlabel("Vth") 
plt.ylabel("accumulation number") 
plt.plot(vth_axis, acc_num_axis)
plt.show()
