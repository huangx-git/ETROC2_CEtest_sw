import numpy as np
import json
import argparse
import matplotlib.pyplot as plt
from yaml import load, Loader


def toPixNum(row, col, w):
    return col*w+row

def fromPixNum(pix, w):
    row = pix%w
    col = int(np.floor(pix/w))
    return row, col

argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--filepath', '-f',  action='store', help="path to file")
argParser.add_argument('--module', '-m',  action='store', help="path to file")
argParser.add_argument('--timestamp', '-t',  action='store', help="timestamp")
args = argParser.parse_args()


if args.filepath:
   result_dir = args.filepath
else:
   result_dir = f'results/{args.module}/{args.timestamp}/'

with open(result_dir + 'noise_width.yaml', 'r') as f:
    noise_matrix = np.array(load(f, Loader = Loader))
with open(result_dir + 'baseline.yaml', 'r') as f:
    max_matrix = np.array(load(f, Loader = Loader))
with open(result_dir + 'thresholds.yaml', 'r') as f:
    threshold_matrix = np.array(load(f, Loader = Loader))


N_pix_w = 16

fig, ax = plt.subplots(2,1, figsize=(15,15))
ax[0].set_title("Baseline of threshold scan")
ax[1].set_title("Noise width of threshold scan")
cax1 = ax[0].matshow(max_matrix)
cax2 = ax[1].matshow(noise_matrix)
fig.colorbar(cax1,ax=ax[0])
fig.colorbar(cax2,ax=ax[1])

ax[0].set_xticks(np.arange(N_pix_w))
ax[0].set_yticks(np.arange(N_pix_w))

ax[1].set_xticks(np.arange(N_pix_w))
ax[1].set_yticks(np.arange(N_pix_w))

for i in range(N_pix_w):
    for j in range(N_pix_w):
        text = ax[0].text(j, i, int(max_matrix[i,j]),
                ha="center", va="center", color="w", fontsize="xx-small")

        text1 = ax[1].text(j, i, int(noise_matrix[i,j]),
                ha="center", va="center", color="w", fontsize="xx-small")

fig.savefig(f'{result_dir}/peak_and_noiseWidth_thresholds.png')
fig.savefig(f'{result_dir}/peak_and_noiseWidth_thresholds.pdf')
plt.show()

plt.close(fig)

fig, ax = plt.subplots()
plt.title("Thresholds from auto scan")
cax = ax.matshow(threshold_matrix)
fig.colorbar(cax)
ax.set_xticks(np.arange(N_pix_w))
ax.set_yticks(np.arange(N_pix_w))

for i in range(N_pix_w):
    for j in range(N_pix_w):
        text = ax.text(j, i, int(threshold_matrix[i,j]),
            ha="center", va="center", color="w", fontsize="xx-small")

ax.set_xlabel("Column")
ax.set_ylabel("Row")

fig.savefig(f'{result_dir}/thresholds.png')
fig.savefig(f'{result_dir}/thresholds.pdf')
plt.show()
plt.close(fig)

