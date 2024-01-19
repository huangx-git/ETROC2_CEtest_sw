import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import awkward as ak

from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

import pickle
import json
import os
from tqdm import tqdm
import argparse
from scipy import stats
import sys
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--loc', action = 'store', default = '4,3')
parser.add_argument('--input', action = 'store')
parser.add_argument('--vth_cuts', action = 'store', nargs = 2, type = int, default = [0, 500])
parser.add_argument('--cal_cuts', action = 'store', nargs = 2, type = int, default = [5000])
parser.add_argument('--nl1a', action = 'store', type = int, default = 3200)
parser.add_argument('--delay', action = 'store', type = int, default = 504)
parser.add_argument('--nbins', action = 'store', type = int, default = 10)
parser.add_argument('--plotted_vths', action = 'store', nargs = '*', default = [250, 255, 260, 292, 299, 340], type = int)
parser.add_argument('--hits_cut', action = 'store', type = float, default = 0)
args = parser.parse_args()

if args.loc == 'broadcast':
    loc_title = 'Broadcasted'
    pix_path = 'broadcast/'
else:
    i = int(args.loc.split(',')[0])
    j = int(args.loc.split(',')[1])
    loc_title = f'Row {i} Col {j}'
    pixpath = f'r{i}c{j}/'

#loc_title = ''
delay = args.delay
nl1a = args.nl1a
nbins = args.nbins
fileform = f'Qinj_scan_L1A_{delay}'
low_cut = np.min(args.vth_cuts)
high_cut = np.max(args.vth_cuts)
low_cal = np.min(args.cal_cuts)
high_cal = np.max(args.cal_cuts)
labfontsize = 20
titfontsize = 25
hitslim = args.nl1a*args.hits_cut
path = args.input + '/' #+ pixpath
if len(args.vth_cuts) == 0 and len(args.cal_cuts) == 0 and args.hits_cut == 0: 
    store = path + 'full_range_qinj_plots/'
else:
    store = path
    if len(args.vth_cuts) > 0:
        store += f'vth{low_cut}_{high_cut}_'
    if len(args.cal_cuts):
        store += f'cal{low_cal}_{high_cal}_'
    if args.hits_cut > 0: 
        store += f'hits_{args.hits_cut}_'.replace('.', 'p')
    store += 'qinj_plots/'
files = [f for f in os.listdir(path) if fileform in f]
if not os.path.isdir(store):
    os.mkdir(store)

figsize = (9, 7)
errorbarsize = (12, 7)

#Loading In Data
if len(files) == 0:
    print('No files here.')
    sys.exit(0)

print(f'Loading the following files from {path}')

df = pd.DataFrame()
for f in files:
    print(f)
    charge = int(f.split('_')[4].split('.')[0])
    if '.pkl' in f:
        sub = pickle.load(open(path+f, 'rb'))
    else:
        with open(path + f, 'r') as infile:
            sub = pd.DataFrame(yaml.load(infile, Loader = yaml.FullLoader))
    sub['charge'] = [charge]*len(sub.vth)
    if not len(np.unique(sub.hits)) == 1:
        df = pd.concat([df, sub])

print()
print(df.head())
if df.empty:
    print('Files found but no hits found.')
    sys.exit(0)

#Slide 3 S Curve Plots
#Hits v. Threshold DAC Values, All QSel

print('Working on Hits v. Threshold DAC')
fig = plt.figure(figsize = figsize)
plt.title(f'Hits v. Threshold DAC {loc_title}\nDelay = {delay}, # of L1A triggers: {nl1a}', fontsize = titfontsize)
plt.xlabel('Threshold DAC Values', fontsize = labfontsize)
plt.ylabel('Hits',  fontsize = labfontsize)

for q in tqdm(np.unique(df.charge)):
    idx = df.charge == q
    x = df.vth[idx]
    y = df.hits[idx]
    plt.plot(x, y, 'o-', label = f'Qinj = {q}')
plt.legend()
plt.savefig(f'{store}/DAC_v_Hits.pdf')
plt.savefig(f'{store}/DAC_v_Hits.png')
plt.show()
plt.close()

#Slide 4 S Curve Plots
#Hits v. Threshold DAC, Individual QSel

for q in tqdm(np.unique(df.charge)):
    fig = plt.figure(figsize = figsize)
    plt.title(f'Hits v. Threshold DAC for Qinj = {q} {loc_title}\nDelay = {delay}, # of L1A triggers: {nl1a}')
    plt.xlabel('Threshold DAC Values')
    plt.ylabel('Hits')

    idx = df.charge == q
    x = df.vth[idx]
    y = df.hits[idx]
    plt.plot(x, y, 'o-')
    plt.savefig(f'{store}/DAC_v_Hits_q{q}.pdf')
    plt.savefig(f'{store}/DAC_v_Hits_q{q}.png')
    plt.close()


temp = pd.DataFrame()
for q in np.unique(df.charge):
    sub = df[df.charge == q]
    idx = [df.charge.iloc[i] == q and df.hits.iloc[i] > hitslim and df.vth.iloc[i] < high_cut and df.vth.iloc[i] > low_cut for i in range(len(df.hits))]
    sub = df[idx]
    temp = pd.concat([temp, sub])

del df
df = temp

print('Working on Hits v. Threshold DAC Redux')
fig = plt.figure(figsize = figsize)
plt.title(f'Hits v. Threshold DAC {loc_title}\nDelay = {delay}, # of L1A triggers: {nl1a}')
plt.xlabel('Threshold DAC Values')
plt.ylabel('Hits')

for q in tqdm(np.unique(df.charge)):
    idx = df.charge == q
    x = df.vth[idx]
    y = df.hits[idx]
    plt.plot(x, y, 'o-', label = f'Qinj = {q}')

plt.legend()
plt.savefig(f'{store}/DAC_v_Hits_redux.pdf')
plt.savefig(f'{store}/DAC_v_Hits_redux.png')
plt.show()
plt.close()

for q in tqdm(np.unique(df.charge)):
    fig = plt.figure(figsize = figsize)
    plt.title(f'Hits v. Threshold DAC for Qinj = {q} {loc_title}\nDelay = {delay}, # of L1A triggers: {nl1a}')
    plt.xlabel('Threshold DAC Values')
    plt.ylabel('Hits')

    idx = df.charge == q
    x = df.vth[idx]
    y = df.hits[idx]
    plt.plot(x, y, 'o-')
    plt.savefig(f'{store}/DAC_v_Hits_q{q}_redux.pdf')
    plt.savefig(f'{store}/DAC_v_Hits_q{q}_redux.png')
    plt.close()


fig, ax = plt.subplots(figsize = figsize)
charges = []
firstbest = []
for q in np.unique(df.charge):
    data = df[df.charge == q]
    best = np.max(data.hits)
    if best >= hitslim:
        charges.append(q)
        firstbest.append(data.vth[data.hits >= hitslim].iloc[-1])
ax.scatter(charges, firstbest, label = 'Data', color = 'r')
model = stats.linregress(charges, firstbest)
x = np.linspace(np.min(charges), np.max(charges), 1000)
y = x*model.slope + model.intercept
ax.plot(x, y, label = 'Fit', color = 'b')

'''
p = 0.05
ts = np.abs(stats.t.ppf(p/2, len(charges) - 2))
slopeerr = ts*model.slope
interr = ts*model.intercept
print(model.slope, model.intercept, ts)
high = x*(model.slope + slopeerr) + (model.intercept+interr)
low = x*(model.slope - slopeerr) + (model.intercept-interr)
ax.fill_between(x, low, high, label = '95% Conf. Int.', alpha = 0.4, color = 'c')
'''

ax.set_title('S-Curve End Points')
ax.set_xlabel('Qinj')
ax.set_ylabel('Threshold DAC')
plt.savefig(f'{store}/Threshold_DAC_Limit.png')
plt.savefig(f'{store}/Threshold_DAC_Limit.png')
plt.show()
plt.close()

#Slide 5 TOT, etc. Distributions at indivudial QSel, 5 different Threshold DACs

print('Working on TOT, TOA, and Cal hists for individual settings')
for q in [25]:#tqdm(np.unique(df.charge)):
    for d in tqdm(args.plotted_vths, leave = False, desc = f'Working on QSel = {q}'):
        #if not d in df.vth: d = np.random.choice(df.vth, 1)
        idx = [df.charge.iloc[i] == q and df.vth.iloc[i] == d for i in range(len(df.vth))]

        fig = plt.figure(figsize = figsize)
        tot = df.tot[idx].iloc[0]
        plt.hist(tot, bins = nbins, density = True)#bins = range(np.min(tot), np.max(tot) + 1), density = True)
        plt.title(f'TOT Values for Threshold DAC = {d} {loc_title}\nEntries: {nl1a}, Delay = {delay}, Qinj = {q}')
        plt.xlabel('TOT Values')
        plt.ylabel('Frequency')
        plt.yscale('log')
        plt.savefig(f'{store}/TOT_vth_{d}_q{q}.pdf')
        plt.savefig(f'{store}/TOT_vth_{d}_q{q}.png')
        plt.close()

        fig = plt.figure(figsize = figsize)
        toa = df.toa[idx].iloc[0]
        plt.hist(toa, bins = nbins, density = True)#bins = range(np.min(toa), np.max(toa) + 1), density = True)
        plt.title(f'TOA Values for Threshold DAC = {d} {loc_title}\nEntries: {nl1a}, Delay = {delay}, Qinj = {q}')
        plt.xlabel('TOA Values')
        plt.ylabel('Frequency')
        plt.yscale('log')
        plt.savefig(f'{store}/TOA_vth_{d}_q{q}.pdf')
        plt.savefig(f'{store}/TOA_vth_{d}_q{q}.png')
        plt.close()

        fig = plt.figure(figsize = figsize)
        cal = df.cal[idx].iloc[0]
        plt.hist(cal, bins = nbins, density = True)#bins = range(np.min(cal), np.max(cal) + 1), density = True)
        plt.title(f'CaL Values for Threshold DAC = {d} {loc_title}\nEntries: {nl1a}, Delay = {delay}, Qinj = {q}')
        plt.xlabel('CAL Values')
        plt.ylabel('Frequency')
        plt.savefig(f'{store}/CAL_vth_{d}_q{q}.pdf')
        plt.savefig(f'{store}/CAL_vth_{d}_q{q}.png')
        plt.close()

#Slide ^

print('Working on TOA v. DAC')

for q in tqdm(np.unique(df.charge)):
    chargeidx = df.charge == q
    hitsidx = df.hits[chargeidx] > hitslim

    vth = df.vth[chargeidx][hitsidx]

    toa = df.toa[chargeidx][hitsidx]
    toaavg = [np.mean(dat) for dat in toa] 
    toastd = [np.std(dat) for dat in toa]

    tot = df.tot[chargeidx][hitsidx]
    totavg = [np.mean(dat) for dat in tot]
    totstd = [np.std(dat) for dat in tot]

    cal = df.cal[chargeidx][hitsidx]
    calavg = [np.mean(dat) for dat in cal]
    calstd = [np.std(dat) for dat in cal]
    
    fig = plt.figure(figsize = errorbarsize)
    plt.errorbar(vth, toaavg, toastd, fmt = 'o-', capsize = 3)
    plt.xlabel('Threshold DAC', fontsize = labfontsize)
    plt.ylabel('TOA Mean', fontsize = labfontsize)
    plt.title(f'Mean TOA vs. Theshold DAC for Delay = {delay} {loc_title}, Qinj = {q}', fontsize = titfontsize) 
    plt.savefig(f'{store}/DAC_v_TOA_q{q}.pdf')
    plt.savefig(f'{store}/DAC_v_TOA_q{q}.png')
    plt.close()

    fig = plt.figure(figsize = errorbarsize)
    plt.errorbar(vth, totavg, totstd, fmt = 'o-', capsize = 3)
    plt.xlabel('Threshold DAC', fontsize = labfontsize)
    plt.ylabel('TOA Mean', fontsize = labfontsize)
    plt.title(f'Mean TOA vs. Theshold DAC for Delay = {delay} {loc_title}, Qinj = {q}', fontsize = titfontsize)
    plt.savefig(f'{store}/DAC_v_TOT_q{q}.pdf')
    plt.savefig(f'{store}/DAC_v_TOT_q{q}.png')
    plt.close()

    fig = plt.figure(figsize = errorbarsize)
    plt.errorbar(vth, calavg, calstd, fmt = 'o-', capsize = 3)
    plt.xlabel('Threshold DAC', fontsize = labfontsize)
    plt.ylabel('CAL Mean', fontsize = labfontsize)
    plt.title(f'Mean CAL vs. Theshold DAC for Delay = {delay} {loc_title}, Qinj = {q}', fontsize = labfontsize)
    plt.savefig(f'{store}/DAC_v_CAL_q{q}.pdf')
    plt.savefig(f'{store}/DAC_v_CAL_q{q}.png')
    plt.close()


fig = plt.figure(figsize = errorbarsize)
for q in tqdm(np.unique(df.charge)):
    chargeidx = df.charge == q
    hitsidx = df.hits[chargeidx] >= hitslim#== nl1a
    vth = df.vth[chargeidx][hitsidx]
    toa = df.toa[chargeidx][hitsidx]
    toaavg = [np.mean(dat) for dat in toa]
    toastd = [np.std(dat) for dat in toa]
    if len(toa) > 2:
        plt.errorbar(vth, toaavg, toastd, alpha = 0.7, capsize = 5, label = f'Qinj = {q}')
plt.xlabel('Threshold DAC', fontsize = labfontsize)
plt.ylabel('TOA Mean', fontsize = labfontsize)
plt.legend()
plt.title(f'Mean TOA vs. Theshold DAC for Delay = {delay} {loc_title}', fontsize = titfontsize)
plt.savefig(f'{store}/DAC_v_TOA.pdf')
plt.savefig(f'{store}/DAC_v_TOA.png')
plt.show()
plt.close()

fig = plt.figure(figsize = errorbarsize)
for q in tqdm(np.unique(df.charge)):
    chargeidx = df.charge == q
    hitsidx = df.hits[chargeidx] >= hitslim#== nl1a
    vth = df.vth[chargeidx][hitsidx]
    tot = df.tot[chargeidx][hitsidx]
    totavg = [np.mean(dat) for dat in tot]
    totstd = [np.std(dat) for dat in tot]
    if len(tot) > 2:
        plt.errorbar(vth, totavg, totstd, alpha = 0.7, capsize = 5, label = f'Qinj = {q}')
plt.xlabel('Threshold DAC', fontsize = labfontsize)
plt.ylabel('TOT Mean', fontsize = labfontsize)
plt.legend()
plt.title(f'Mean TOT vs. Theshold DAC for Delay = {delay} {loc_title}', fontsize = titfontsize)
plt.savefig(f'{store}/DAC_v_TOT.pdf')
plt.savefig(f'{store}/DAC_v_TOT.png')
plt.show()
plt.close()

fig = plt.figure(figsize = errorbarsize)
for q in tqdm(np.unique(df.charge)):
    chargeidx = df.charge == q
    hitsidx = df.hits[chargeidx] >= hitslim
    vth = df.vth[chargeidx][hitsidx]
    cal = df.cal[chargeidx][hitsidx]
    calavg = [np.mean(dat) for dat in cal]
    calstd = [np.std(dat) for dat in cal]
    if len(cal) > 2:
        plt.errorbar(vth, calavg, calstd, alpha = 0.7, capsize = 5, label = f'Qinj = {q}')
plt.xlabel('Threshold DAC', fontsize = labfontsize)
plt.ylabel('CAL Mean', fontsize = labfontsize)
plt.title(f'Mean CAL vs. Theshold DAC for Delay = {delay} {loc_title}', fontsize = titfontsize)
plt.savefig(f'{store}/DAC_v_CAL.pdf')
plt.savefig(f'{store}/DAC_v_CAL.png')
plt.show()
plt.close()


# Polynomial Regression of TOA SD data
'''
for q in np.unique(df.charge):
    idx = df.charge == q
    vth = df.vth[idx]
    toa = df.toa[idx]
    x = []
    y = []
    
    for i in range(len(vth)):
        #print(df.hits[idx].iloc[i], len(toa.iloc[i]))
        if len(toa.iloc[i]) > .98*nl1a:# and np.std(toa.iloc[i]) < 2:#> .98*nl1a :
            x.append(vth.iloc[i])
            y.append(np.std(toa.iloc[i]))
    
    if len(x) > 10: 
        fig = plt.figure(figsize = figsize) 

        transformer = PolynomialFeatures(degree = 4)
        model = LinearRegression(fit_intercept = True)

        plt.plot(x, y, 'o-', alpha = 0.8, label = 'Data')
        
        X = transformer.fit_transform(np.array(x).reshape(-1, 1))
        model.fit(X, y)
         
        x = np.array(vth).reshape(-1, 1)
        X = transformer.fit_transform(x)
        y = model.predict(X)
        
        plt.plot(x, y, label = 'Fit')

        ydiff = [y[i] - y[i-1] for i in range(1, len(y))]
        lim = 0.05
        starter = [diff > -lim for diff in ydiff]
        ender = [diff < lim for diff in ydiff]
        startidx = starter.index(True)
        ender.reverse()
        endidx = len(ender) - ender.index(True)
        x = [vth[startidx]]*10 + [np.nan] + [vth[endidx]]*10
        y = np.linspace(0, 2, 10).tolist() + [0] + np.linspace(0, 2, 10).tolist()
        plt.plot(x, y, label = 'Boundaries')
        
        plt.plot([x[0], x[len(x) - 1]], [0.5, 0.5], label = 'TOA SD = 0.5')
        plt.plot([x[0], x[len(x) - 1]], [1, 1], label = 'TOA SD = 1')
        
        plt.ylim([0, 2])
        plt.xlabel('Threshold DAC')
        plt.ylabel('CAL Std Dev.')
        plt.legend()
        plt.title(f'Standard Deviation of TOA vs. Theshold DAC for Delay = {delay}\n {loc_title}, Qinj = {q}')
        plt.savefig(f'{store}/DAC_v_TOASD_q{q}.pdf')
        plt.savefig(f'{store}/DAC_v_TOASD_q{q}.png')
        plt.close()
        

'''
fig = plt.figure(figsize = figsize)
for q in np.unique(df.charge):
    idx = df.charge == q
    vth = df.vth[idx]
    toa = df.toa[idx]
    x = []
    y = []

    for i in range(len(vth)):
        #print(df.hits[idx].iloc[i], len(toa.iloc[i]))
        if len(toa.iloc[i]) >= hitslim:# and np.std(toa.iloc[i]) < 2:#> .98*nl1a :
            x.append(vth.iloc[i])
            y.append(np.std(toa.iloc[i]))

    if len(x) > 10:
        plt.plot(x, y, 'o-', alpha = 0.8, label = f'Qinj = {q}')
        
plt.plot([x[0], x[len(x) - 1]], [0.5, 0.5], label = 'TOA SD = 0.5')
plt.plot([x[0], x[len(x) - 1]], [1, 1], label = 'TOA SD = 1')

plt.ylim([0, 2])
plt.xlabel('Threshold DAC')
plt.ylabel('CAL Std Dev.')
plt.legend()
plt.title(f'Standard Deviation of TOA vs. Theshold DAC for Delay = {delay}\n {loc_title}')
plt.savefig(f'{store}/DAC_v_TOASD.pdf')
plt.savefig(f'{store}/DAC_v_TOASD.png')
plt.show()
plt.close()


'''
# TOA v. TOT 

for q in np.unique(df.charge):
    x = []
    y = []
    a = []
    idx = [df.hits.iloc[i] > 0 and df.charge.iloc[i] == q for i in range(len(df.hits))]
    keptvths = []
    for d in np.unique(df.vth[idx]):
        idx = [df.charge.iloc[i] == q and df.vth.iloc[i] == d for i in range(len(df.charge))]
        lim = np.max(df.hits[idx])
        idx =  [df.charge.iloc[i] == q and df.vth.iloc[i] == d and df.hits.iloc[i] == lim for i in range(len(df.charge))]
        if any(idx):
            x.append([np.mean(df.tot[idx].iloc[0])])
            y.append([np.mean(df.toa[idx].iloc[0])])
            a.append(len(df.toa[idx].iloc[0]))
            keptvths.append(d)
    a = np.array(a)
    a = a - np.min(a)
    a = a/np.max(a)
    fig, ax = plt.subplots(figsize = figsize)
    color = plt.cm.get_cmap('winter')
    c = [i/len(x) for i in range(len(x))]
    pos = ax.scatter(x, y, c = c, vmin = 0, vmax = 1, alpha = a, cmap = color)
    cbar = plt.colorbar(pos, ax = ax, label = 'Threshold DAC')
    cbar.set_ticks([0, 1])
    cbar.set_ticklabels([np.min(keptvths), np.max(keptvths)])
    ax.set_title(f'Mean TOT values v. Mean TOA Values {loc_title}\nDelay = {delay}, Qinj = {q}')
    ax.set_xlabel('Mean TOT')
    ax.set_ylabel('Mean TOA')
    plt.savefig(f'{store}/TOT_v_TOA_{q}.png')
    plt.savefig(f'{store}/TOT_v_TOA_q{q}.pdf')
    plt.close()

fig, ax = plt.subplots(figsize = figsize)
for q in np.unique(df.charge):
    x = []
    y = []
    idx = [df.charge.iloc[i] == q for i in range(len(df.hits))]
    lim = np.max(df.hits[idx])
    idx = [df.charge.iloc[i] == q and df.hits.iloc[i] == lim for i in range(len(df.hits))]
    sub = df[idx]
    for i in range(len(sub.vth)):
        if np.abs(sub.hits.iloc[i] -  np.max(sub.hits))/np.max(sub.hits) < 0.05:
            x += sub.tot.iloc[i]
            y += sub.toa.iloc[i]
    plt.plot(x, y, 'o-', label = f'Qinj = {q}')
    
ax.set_title(f'TOT values v. TOA Values {loc_title}\nDelay = {delay}')
ax.set_xlabel('Time over Threshold')
ax.set_ylabel('Time of Arrival')
plt.legend()
plt.savefig(f'{store}/TOT_v_TOA_full.png')
plt.savefig(f'{store}/TOT_v_TOA_full.pdf')
plt.close()
'''
