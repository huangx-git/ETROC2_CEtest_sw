#!/usr/bin/env python3

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import json

with open('eye_scan_results/data.json', 'r') as openfile:
    eye_data = json.load(openfile)

(fig, axs) = plt.subplots(1, 1, figsize=(10, 8))
print ("fig type = " + str(type(fig)))
print ("axs type = " + str(type(axs)))
axs.set_title("LpGBT 2.56 Gbps RX Eye Opening Monitor")
plot = axs.imshow(eye_data, alpha=0.9, vmin=0, vmax=100, cmap='jet',interpolation="nearest", aspect="auto",extent=[-384.52/2,384.52/2,-0.6,0.6,])
plt.xlabel('ps')
plt.ylabel('volts')
fig.colorbar(plot, ax=axs)

plt.show()
