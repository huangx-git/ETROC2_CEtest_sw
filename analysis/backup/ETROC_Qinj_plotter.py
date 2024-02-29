#!/usr/bin/env python
# coding: utf-8

# In[4]:


import sys
import numpy as np
from datetime import datetime
import time
import re
import gc    #garbage collector
import os
import pickle
import matplotlib.pyplot as plt

import general_custom_utils as gcu
#import plotting_utils as pu
import mplhep as hep

SAVE_PLOT = True
MAKE_GIF = False
CMS_STYLE = True

FIG_FORMAT = 'pdf'  # must be either 'pdf' (pref) or 'png'
W_FIGURE = 12
H_FIGURE = 8
FONT_SIZE = 16

## PHYSICS PARAMETERS
Vth_noise = 265  # 550
DEFAULT_DELAY = 504
L1A_SENT = 3200  # 3200     # it will be overwritten
MIN_HITS = 0.95 * L1A_SENT  # calculate mean and std dev only if hits > MIN_HITS

print("  " + datetime.now().strftime("\n  %Y %B %d  - %I:%M:%S %p") + " - STARTED!\n")

INPUT_PATH = "/home/daq/ETROC2_Test_Stand/module_test_sw/results/delay_10_scans/"

is_running_in_notebook = False
# Definition of the variable is_running_in_notebook
try:
    from IPython import get_ipython
    if get_ipython() is not None:
        is_running_in_notebook = True
except ImportError:
    is_running_in_notebook = False

if not is_running_in_notebook:
    # Code is not in a notebook, ask the user for the path
    user_input_path = input("  Enter the path of the folder containing the charge injection pickle files: \n")
    if user_input_path.strip() != "":
        INPUT_PATH = user_input_path.strip()

print()

#print("is_running_in_notebook:\t", is_running_in_notebook)
#print("INPUT_PATH:    \t", INPUT_PATH)


# define a folder name with today's date + an incremental number
# (folder will be created only if needed)
if INPUT_PATH[-1:0] == "/":
    INPUT_PATH = INPUT_PATH[:-1]
output_folder = INPUT_PATH+"/plots/"+datetime.now().strftime("%Y-%m-%d_")
incremental_index = 0
while os.path.exists(output_folder+f"{incremental_index:03d}/"):
#    print (output_folder+f"{incremental_index:03d}/ exists!")
    incremental_index = incremental_index + 1
output_folder = output_folder + f"{incremental_index:03d}/"


# In[ ]:


pickle_files = []

DELAY = None
pix_row = None
pix_col = None
MODULE_BOARD = None
Qinj_VALUES=[]
TOA_range = [None, None]     #        TOA plt.ylim(270,400)
TOT_range = [None, None]     #        TOT plt.ylim(0,150)
CAL_range = [None, None]     #        CAL

# Create an empty dictionary to store the data
Qinj_scan_L1A_data = {}

pattern = re.compile(r'Qinj_scan_L1A_(\d+)_pix_r(\d+)_c(\d+)_q(\d+)_V(\d+)')

print(f"  Picking pickles in {INPUT_PATH}")
for file in gcu.progressBar( os.listdir(INPUT_PATH) , prefix = ' ', suffix = 'Complete', length = 15):
    if file.startswith("Qinj_scan_L1A_") and file.endswith(".pkl"):
        pickle_files.append(file)

        # Grab parameters values from file name
        match = pattern.match(file[:-15])
        if match:
            DELAY = int(match.group(1))
            pix_row = int(match.group(2))
            pix_col = int(match.group(3))
            module_board = int(match.group(5))
            Qinj_VALUES.append(int(match.group(4)))
            key = file[:-15]

            if not DELAY==int(match.group(1)) or not pix_row==int(match.group(2)) or not pix_col==int(match.group(3)) or not module_board==int(match.group(5)):
                print(f"We have different Delays/pix_row/pix_col/module_board in the same folder!")

        else: #it's the Aug01 scan
            DELAY=504
            pix_row = 4
            pix_col = 3
            module_board = 4
            Qinj_VALUES = [2,4,6,8,10,12,15,20,25,30,32]
            key = file[:-4]

        # store pickle data in dictionary
        file_path = os.path.join(INPUT_PATH, file)
        with open(file_path, 'rb') as file:
            Qinj_scan_L1A_data[key] = pickle.load(file)

            L1A_SENT = Qinj_scan_L1A_data[key]['hits'].max()
            MIN_HITS = 0.95*L1A_SENT            # calculate mean and std dev only if hits>MIN_HITS

Qinj_VALUES=sorted(Qinj_VALUES)

print(f"\n  Scan parameters:")
print(f"  L1Atriggers= {L1A_SENT}, DELAY= {DELAY}, pix_row={pix_row}, pix_col={pix_col}, module_board={module_board}")
print(f"  Qinj_VALUES= {Qinj_VALUES}\n")


#print ( f"Key= {key_generator()}")
#check_if_pickle_exists("Qinj_scan_L1A_504_pix_r10_c12_8_V04")



# In[ ]:


Qinj_DEFAULT = Qinj_VALUES[int(0.5*len(Qinj_VALUES))]

# ----------------------------------------------------------------------------------------------------------------------------------------
def key_generator(delay=DELAY, pix_row=pix_row, pix_col=pix_col, Qinj=Qinj_DEFAULT):
    if "Aug01" in INPUT_PATH or "Jul28" in INPUT_PATH:
        generated_key = f'Qinj_scan_L1A_{delay}_{Qinj}'
#    elif "Aug02" in INPUT_PATH:
#        generated_key = f'Qinj_scan_L1A_{delay}_pix_r{pix_row}_c{pix_col}_q{Qinj}_V{module_board:02d}'
    else:
        generated_key = f'Qinj_scan_L1A_{delay}_pix_r{pix_row}_c{pix_col}_q{Qinj}_V{module_board:02d}'

    # check if pickle exists
    if not any(file_name.startswith(key) for file_name in pickle_files):
#    if key+".pkl" not in pickle_files:
        print(f"Scan '{key}' not found in the pickle_files. Here's our pickles:")
        for file_name in pickle_files:
            print(  str(file_name)+"  \t key:  "+str(file_name[:-4]) )
        raise ValueError(f"Scan '{key}' not found in the pickle_files. Please check if the scan exists or provide the correct delay and Qinj values.")

    return generated_key


# ----------------------------------------------------------------------------------------------------------------------------------------
def plot_hits_vs_vth(delay=DELAY, Qinj_values=Qinj_DEFAULT, save_plot=False):

    # Create a scatter plot of "hits" and "vth" columns from the DataFrame
    plt.figure(figsize=( W_FIGURE, H_FIGURE))

    if not isinstance(Qinj_values, list):
        Qinj_values = [Qinj_values]

    for Qinj in Qinj_values:
        key = key_generator(delay, pix_row, pix_col, Qinj)

        plt.scatter(Qinj_scan_L1A_data[key]['vth'], Qinj_scan_L1A_data[key]['hits']/L1A_SENT, s=20, label=f'Qinj = {Qinj} fC')
        plt.plot(Qinj_scan_L1A_data[key]['vth'], Qinj_scan_L1A_data[key]['hits']/L1A_SENT, linestyle='-', alpha=0.3)

        # PRINT VTH FOR WHICH WE OBSERVE A DROP IN HITS
        selected_data = Qinj_scan_L1A_data[key][(Qinj_scan_L1A_data[key]['hits'] > 0.5*L1A_SENT) & (Qinj_scan_L1A_data[key]['hits'] < 0.99*L1A_SENT)]
        # save text in order to add it as annotation within the plot
        hitdrop_printout = '\n'.join([f"vth: {int(row['vth'])}, hits: {int(row['hits'])}" for _, row in selected_data[['vth', 'hits']].iterrows()])

    plt.xlabel('Threshold DAC Values', fontsize=FONT_SIZE)
    plt.ylabel('Hits', fontsize=FONT_SIZE)
    plt.grid(True, linestyle='dotted', linewidth=0.5)
    plt.tick_params(axis='both', which='major', labelsize=0.9*FONT_SIZE)

    plt.xlim(400,1000)
    if CMS_STYLE:
        plt.style.use(hep.style.CMS)
        hep.cms.label(loc=1, llabel="ETL Preliminary", rlabel="")
        plt.ylim(0,1.19)

    if len(Qinj_values)>1:
        plt.title(f'Hits vs. Threshold DAC.\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, # of L1Atriggers: {L1A_SENT}', fontsize=1.2*FONT_SIZE)
        plt.legend(loc='best', fontsize=1.*FONT_SIZE) # 'upper left'
    else:
        plt.title(f'Hits vs. Threshold DAC for Qinj= {Qinj_values[0]} fC.\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, # of L1Atriggers: {L1A_SENT}', fontsize=1.2*FONT_SIZE)

    if save_plot:
        gcu.create_output_folder( output_folder )
        if len(Qinj_values)>1:
            plt.savefig( output_folder+f'hits_vs_vth_V{module_board:02d}_r{pix_row}_c{pix_col}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
            if is_running_in_notebook:
                plt.show()
        else:
            gcu.create_output_folder(output_folder+"hits_vs_vth/")
            if MAKE_GIF:
                gcu.create_output_folder( output_folder+"hits_vs_vth/gif")
                plt.savefig( output_folder+f'hits_vs_vth/gif/hits_vs_vth_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj_values[0]:02d}.png', format='png', transparent=True, bbox_inches='tight')
            # PRINT VTH FOR WHICH WE OBSERVE A DROP IN HITS
            plt.text(0.95, 0.95, hitdrop_printout, transform=plt.gca().transAxes, verticalalignment='top', horizontalalignment='right', fontsize=0.9*FONT_SIZE)
            plt.savefig( output_folder+f'hits_vs_vth/hits_vs_vth_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj_values[0]}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
    else:
        plt.text(0.95, 0.95, hitdrop_printout, transform=plt.gca().transAxes, verticalalignment='top', horizontalalignment='right', fontsize=0.9*FONT_SIZE)
        if is_running_in_notebook:
            plt.show()
    plt.close()

# ----------------------------------------------------------------------------------------------------------------------------------------
def plot_mean_vs_vth(delay=DELAY, Qinj=Qinj_DEFAULT, column='toa', save_plot=False):
    key = key_generator(delay, pix_row, pix_col, Qinj)
    #check_if_pickle_exists(key)

    column = column.lower().strip()
    if column not in ["toa", "tot", "cal"]:
        raise ValueError(f"Invalid column name '{column}'. Please choose one of toa, tot, cal.")

    # Filter the DataFrame
    selected_data = Qinj_scan_L1A_data[key][ (Qinj_scan_L1A_data[key]['hits'] >0) & (Qinj_scan_L1A_data[key]['vth'] >Vth_noise)]

    # Calculate the mean and RMS (std) of values for each 'vth' value
    mean_noNaN = selected_data.explode(column).groupby('vth')[column].mean().fillna(0)
    mean = selected_data.explode(column).groupby('vth')[column].mean()
    rms = selected_data.explode(column).groupby('vth')[column].std().fillna(0)

    # Create a scatter plot of mean vs. VTH with red circles
    plt.figure(figsize=( W_FIGURE, H_FIGURE))
    plt.scatter(selected_data['vth'], mean_noNaN, s=10, c='red', marker='o')
    plt.errorbar(selected_data['vth'], mean_noNaN, yerr=rms, fmt='none', ecolor='black', capsize=1, alpha=0.3)

    plt.xlabel('Threshold DAC', fontsize=FONT_SIZE)
    plt.ylim(0)  # Set the y-axis to start from 0
    plt.ylabel(f'{column.upper()} Mean', fontsize=FONT_SIZE)
    plt.title(f'Mean {column.upper()} vs. Threshold DAC for V{module_board:02d}, Pixel r{pix_row} c{pix_col}, Qinj = {Qinj} fC', fontsize=1.2*FONT_SIZE)
    plt.grid(True, linestyle='dotted', linewidth=0.5)
    plt.tick_params(axis='both', which='major', labelsize=0.8 * FONT_SIZE)
    if CMS_STYLE:
        plt.style.use(hep.style.CMS)
        hep.cms.label(loc=1, llabel="ETL Preliminary", rlabel="")

    if save_plot:
        gcu.create_output_folder( output_folder+"mean_vs_vth/")
        plt.savefig( output_folder+f'mean_vs_vth/mean{column.upper()}_vs_vth_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
        if MAKE_GIF:
            gcu.create_output_folder( output_folder+"mean_vs_vth/gif")
            plt.savefig( output_folder+f'mean_vs_vth/gif/mean{column.upper()}_vs_vth_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj:02d}.png', format='png', transparent=True, bbox_inches='tight')
    else:
        if is_running_in_notebook:
            plt.show()
    plt.close()



# ----------------------------------------------------------------------------------------------------------------------------------------
def plot_toa_tot_cal_histogram(vth_value, delay=DELAY, qinj=Qinj_DEFAULT, save_plot=False):
    key = key_generator(delay, pix_row, pix_col, qinj)

    # Filter the DataFrame based on the desired "vth" value
    subset_data = Qinj_scan_L1A_data[key][Qinj_scan_L1A_data[key]['vth'] == vth_value]
    if subset_data.empty or subset_data.iloc[0]["toa"]==[]:
        if not save_plot and False:
            print(f"No values found with vth = {vth_value}")
        return
    font_size = FONT_SIZE
    n_bins=20

    # Create a figure with three subplots
    fig, axes = plt.subplots(1, 3, figsize=(H_FIGURE*3, H_FIGURE))

    for i, column in enumerate(["toa", "tot", "cal"]):
        # Calculate the appropriate number of bins
        if max(subset_data.iloc[0][column]) - min(subset_data.iloc[0][column]) < n_bins:
            n_bins = int( 1 + max(subset_data.iloc[0][column]) - min(subset_data.iloc[0][column]) )

        # Plot histogram for the current column
        axes[i].hist(subset_data[column], bins=n_bins, edgecolor='black', alpha=0.6, linewidth=2, density=True)
        axes[i].set_xlabel(f'{column.upper()} Values', fontsize=font_size)
        axes[i].set_ylabel('Frequency', fontsize=font_size)
        axes[i].set_title(f'{column.upper()} Values for Threshold DAC = {vth_value}\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, Entries: {L1A_SENT}, Qinj = {qinj} fC',
                          fontsize=1.2 * font_size)
        axes[i].tick_params(axis='both', which='major', labelsize=0.8 * font_size)
        axes[i].xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        axes[i].grid(True, linestyle='dotted', linewidth=0.5)

    if CMS_STYLE:
        plt.style.use(hep.style.CMS)
        hep.cms.label(loc=1, llabel="ETL Preliminary", rlabel="")

    if save_plot:
        gcu.create_output_folder( output_folder+f"toa_tot_cal_histograms/Qinj{qinj:02d}/")
        plt.savefig( output_folder+f'toa_tot_cal_histograms/Qinj{qinj:02d}/toa_tot_cal_hist_vth{vth_value}_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{qinj:02d}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
    else:
        if is_running_in_notebook:
            plt.show()
    plt.close()
    gc.collect()


# ----------------------------------------------------------------------------------------------------------------------------------------
def plot_mean_vs_vth_vs_Qinj(delay=DELAY, column='toa', plot_errorbars=True, save_plot=False):
    column = column.lower().strip()
    if column not in ["toa", "tot", "cal"]:
        raise ValueError(f"Invalid column name '{column}'. Please choose one of toa, tot, cal.")

    # Create a scatter plot of TOA mean vs. VTH for each Qinj value
    plt.figure(figsize=( W_FIGURE, H_FIGURE))

    for i_qinj, qinj in enumerate(Qinj_VALUES):
        key = key_generator(delay, pix_row, pix_col, qinj)

        # Filter the DataFrame
        selected_data = Qinj_scan_L1A_data[key][ (Qinj_scan_L1A_data[key]['hits']>MIN_HITS) & (Qinj_scan_L1A_data[key]['vth']>Vth_noise) ]

        # Calculate the mean of the specified column values for each 'vth' value
        column_mean_noNaN = selected_data.explode(column).groupby('vth')[column].mean().fillna(0)
        column_mean = selected_data.explode(column).groupby('vth')[column].mean()
        column_rms = selected_data.explode(column).groupby('vth')[column].std().fillna(0)

        if i_qinj == int( 0.5*len(Qinj_VALUES) ) and TOA_range==[None,None] and TOT_range==[None,None] and CAL_range==[None,None]:
            column_mean_of_means = np.average(column_mean.values, weights=1 / column_rms)
            column_rms_of_means = np.sqrt(np.average((column_mean.values - column_mean_of_means)**2, weights=1 / column_rms))
            column_min_of_means = np.min(column_mean.values)

            #print("Column Mean of Means:", column_mean_of_means)
            #print("Column RMS of Means:", column_rms_of_means)
            #print("Column Minimum of Means:", column_min_of_means)

            if column == 'toa':
                TOA_range[1]= column_mean_of_means + 4*column_rms_of_means
                #TOA_range[0]= column_min_of_means
                TOA_range[0]= column_mean_of_means - 4*column_rms_of_means
            elif column == 'tot':
                TOT_range[1]= column_mean_of_means + 4*column_rms_of_means
                TOT_range[0]= 0
                #TOT_range[0]= column_mean_of_means - 4*column_rms_of_means
            elif column == 'cal':
                CAL_range[1]= column_mean_of_means + 12*column_rms_of_means
                CAL_range[0]= column_mean_of_means - 8*column_rms_of_means


        # Create scatter plot for each Qinj value
        plt.scatter(selected_data['vth'], column_mean_noNaN, s=20, marker='o', label=f'Qinj = {qinj} fC')

        # Add error bars with black color and transparency
        if plot_errorbars:
            plt.errorbar(selected_data['vth'], column_mean_noNaN, yerr=column_rms, fmt='none', ecolor='grey', capsize=1, alpha=0.2)

    plt.xlabel('Threshold DAC', fontsize=FONT_SIZE)
    if column == 'toa':
        plt.ylim( TOA_range[0] , TOA_range[1] )
    elif column == 'tot':
        plt.ylim( TOT_range[0] , TOT_range[1] )
    elif column == 'cal':
        plt.ylim( CAL_range[0] , CAL_range[1] )
    plt.ylabel(f'Mean of {column.upper()} values', fontsize=FONT_SIZE)
    plt.title(f'Mean {column.upper()} vs. Threshold DAC for Different Qinj Values.\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, ', fontsize=1.2 * FONT_SIZE)
    plt.grid(True, linestyle='dotted', linewidth=0.5)
    plt.legend(loc='upper right', ncol=2, fontsize=1.*FONT_SIZE)
    plt.tick_params(axis='both', which='major', labelsize=0.8 * FONT_SIZE)
    if CMS_STYLE:
        plt.style.use(hep.style.CMS)
        hep.cms.label(loc=1, llabel="ETL Preliminary", rlabel="")
    if save_plot:
        gcu.create_output_folder( output_folder )
        plt.savefig( output_folder+f'plot_mean{column.upper()}_vs_vth_V{module_board:02d}_r{pix_row}_c{pix_col}_vs_Qinj.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
    if is_running_in_notebook:
        plt.show()
    plt.close()


# ----------------------------------------------------------------------------------------------------------------------------------------
def plot_stdDev_vs_vth_vs_Qinj(delay=DELAY, column='toa', save_plot=False):
    column = column.lower().strip()
    if column not in ["toa", "tot", "cal"]:
        raise ValueError(f"Invalid column name '{column}'. Please choose one of toa, tot, cal.")

    plt.figure(figsize=( W_FIGURE, H_FIGURE))
    for qinj in Qinj_VALUES:
        key = key_generator(delay, pix_row, pix_col, qinj)

        # Filter the DataFrame
        selected_data = Qinj_scan_L1A_data[key][(Qinj_scan_L1A_data[key]['hits'] > MIN_HITS) & (Qinj_scan_L1A_data[key]['vth'] > Vth_noise)]

        # Calculate the mean of the specified column values for each 'vth' value
        column_mean_noNaN = selected_data.explode(column).groupby('vth')[column].mean().fillna(0)
        column_mean = selected_data.explode(column).groupby('vth')[column].mean()
        column_rms = selected_data.explode(column).groupby('vth')[column].std().fillna(0)

        # Create scatter plot for each Qinj value
        plt.scatter(selected_data['vth'], column_rms, s=25, marker='o', label=f'Qinj = {qinj} fC')
        plt.plot(selected_data['vth'], column_rms, linestyle='-', alpha=0.3)

    plt.xlabel('Threshold DAC', fontsize=FONT_SIZE)
    plt.ylim(-0.99,3.99)
    plt.ylabel(f'Std deviation of {column.upper()} values', fontsize=FONT_SIZE)
    plt.title(f'Std Dev. of {column.upper()} vs. Threshold DAC for Different Qinj Values.\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, ', fontsize=1.2 * FONT_SIZE)
    plt.grid(True, linestyle='dotted', linewidth=0.5)
    plt.legend(loc='lower center', ncol=4, fontsize=1.*FONT_SIZE)
    plt.tick_params(axis='both', which='major', labelsize=0.8 * FONT_SIZE)
    if CMS_STYLE:
        plt.style.use(hep.style.CMS)
        hep.cms.label(loc=1, llabel="ETL Preliminary", rlabel="")
    if save_plot:
        gcu.create_output_folder( output_folder )
        plt.savefig( output_folder+f'plot_stddev{column.upper()}_vs_vth_vs_Qinj_V{module_board:02d}_r{pix_row}_c{pix_col}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
    if is_running_in_notebook:
        plt.show()
    plt.close()

# ----------------------------------------------------------------------------------------------------------------------------------------
def plot_hist2D_TOA_vs_TOT(delay=DELAY, Qinj_values=Qinj_DEFAULT, save_plot=False):

    if not isinstance(Qinj_values, list):
        Qinj_values = [Qinj_values]

    plt.figure(figsize=( W_FIGURE, H_FIGURE))

    for qinj in Qinj_values:
        key = key_generator(delay, pix_row, pix_col, qinj )

        # Filter the DataFrame
        selected_data = Qinj_scan_L1A_data[key][(Qinj_scan_L1A_data[key]['hits'] > 0) & (Qinj_scan_L1A_data[key]['vth'] > Vth_noise)]

        # Calculate the mean of TOA and TOT values for each 'vth' value
        column = 'toa'
        toa_mean = selected_data.explode(column).groupby('vth')[column].mean().fillna(0)
        toa_rms = selected_data.explode(column).groupby('vth')[column].std().fillna(0)
        column = 'tot'
        tot_mean = selected_data.explode(column).groupby('vth')[column].mean().fillna(0)
        tot_rms = selected_data.explode(column).groupby('vth')[column].std().fillna(0)

        plt.hist2d( tot_mean , toa_mean , bins=200, cmap='viridis', density=True)


    if CMS_STYLE:
        plt.style.use(hep.style.CMS)
        hep.cms.label(loc=1, llabel="ETL Preliminary", rlabel="")

    if len(Qinj_values)>1:
        plt.title(f'Mean of TOA vs. Mean of TOT for Different Qinj Values.\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, ', fontsize=1.2 * FONT_SIZE)
    else:
        plt.title(f'Mean of TOA vs. Mean of TOT for Qinj={Qinj_values[0]} fC.\nV{module_board:02d}, Pixel r{pix_row} c{pix_col}, ', fontsize=1.2 * FONT_SIZE)

    plt.grid(True, linestyle='dotted', linewidth=0.5)
    #plt.legend(loc='lower center',ncol=4)
    plt.tick_params(axis='both', which='major', labelsize=0.8 * FONT_SIZE)

    plt.xlabel(f'Mean of TOT values', fontsize=FONT_SIZE)
    plt.xlim( TOT_range[0] , TOT_range[1] )
    plt.ylabel(f'Mean of TOA values', fontsize=FONT_SIZE)
    plt.ylim( TOA_range[0] , TOA_range[1] )

    if save_plot:
        if len(Qinj_values)>1:
            gcu.create_output_folder( output_folder )
            plt.savefig( output_folder+f'plot_TOA_vs_TOT_hist2D_Qinjs.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
        else:
            gcu.create_output_folder(output_folder+"TOA_vs_TOT_hist2D/")
            plt.savefig( output_folder+f'TOA_vs_TOT_hist2D/TOA_vs_TOT_hist2D_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj_values[0]}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
            if MAKE_GIF:
                gcu.create_output_folder(output_folder+"TOA_vs_TOT_hist2D/gif")
                plt.savefig( output_folder+f'TOA_vs_TOT_hist2D/gif/TOA_vs_TOT_hist2D_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj_values[0]:02d}.png', format='png', transparent=True, bbox_inches='tight')
    if is_running_in_notebook:
        plt.show()
    plt.close()


# In[ ]:


# check if the Vth register value is effective immediately (if not we should see a trend of TOA adjusting to the Vth value)

def plot_toa_vs_index_for_vth(delay=DELAY, Qinj=Qinj_DEFAULT, selected_vths=None, save_plot=False):
    if selected_vths is None:
        selected_vths = [580,600,650,700]  # Provide the vth values you're interested in plotting

    key = key_generator(delay, pix_row, pix_col, Qinj)

    # Filter the DataFrame
    selected_data = Qinj_scan_L1A_data[key][(Qinj_scan_L1A_data[key]['hits'] > 0) & (Qinj_scan_L1A_data[key]['vth'] > Vth_noise)]

    # Create a scatter plot of toa vs. index for selected vth values
    plt.figure(figsize=(W_FIGURE, H_FIGURE))

    for vth in selected_vths:
        print(f"Found TOA for vth = {vth}")
        vth_data = selected_data[selected_data['vth'] == vth]

        if vth_data.empty:
            print(f"No TOA for this vth = {vth} and Qinj = {Qinj}")
        else:
            toa_values = vth_data['toa'].iloc[0]
            index_values = range(len(toa_values))
            plt.scatter(index_values, toa_values, label=f'Vth = {vth}', s=10)

    plt.xlabel('Index', fontsize=FONT_SIZE)
    plt.ylabel('TOA', fontsize=FONT_SIZE)
    plt.title(f'TOA vs. Index for V{module_board:02d}, Pixel r{pix_row} c{pix_col}, Qinj = {Qinj} fC', fontsize=1.2 * FONT_SIZE)
    plt.grid(True, linestyle='dotted', linewidth=0.5)
    plt.tick_params(axis='both', which='major', labelsize=0.8 * FONT_SIZE)
    plt.legend()

    if save_plot:
        gcu.create_output_folder(output_folder + "toa_vs_index/")
        plt.savefig(output_folder + f'toa_vs_index/toa_vs_index_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj}.{FIG_FORMAT}', format=FIG_FORMAT, transparent=True, bbox_inches='tight')
#        if MAKE_GIF:
#            gcu.create_output_folder(output_folder + "toa_vs_index/gif")
#            plt.savefig(output_folder + f'toa_vs_index/gif/toa_vs_index_V{module_board:02d}_r{pix_row}_c{pix_col}_Qinj{Qinj:02d}.png', format='png', transparent=True, bbox_inches='tight')
        plt.close()
    else:
        if is_running_in_notebook:
            plt.show()

#  ------------------------------------------------------------------------------------------------------------
# this check was already performed and no trend was observed so the function is not called.
#for Qinj in Qinj_VALUES:
#        plot_toa_vs_index_for_vth(delay=504, Qinj=Qinj, selected_vths=None, save_plot=False)


# In[ ]:


#plot_toa_tot_cal_histogram(vth_value=600)

if SAVE_PLOT and False:  # very time consuming and !!! MEMORY LEAK OBSERVED --> FIX THIS
    # histograms only for qinj = 12
    for vth in gcu.progressBar( range(250,1000), prefix = '  Making TOA, TOT and CAL histograms vs Vth:\t ', suffix = 'Complete', length = 15):
        plot_toa_tot_cal_histogram(vth, qinj=12, save_plot=SAVE_PLOT)

    # histograms for all Qinj values
#    for vth in gcu.progressBar( range(250,1000), prefix = 'Making TOA, TOT and CAL histograms vs Vth:\t ', suffix = 'Complete', length = 15):
#        for Qinj in Qinj_VALUES:
#            plot_toa_tot_cal_histogram(vth, qinj=Qinj, save_plot=SAVE_PLOT)


#else:
#    for vth in range(450,750):
#        plot_toa_tot_cal_histogram(vth, Qinj=10, save_plot=SAVE_PLOT)


# In[ ]:


#plot_hits_vs_vth(delay=504, Qinj_values=25)

for Qinj in Qinj_VALUES:
    plot_hits_vs_vth(delay=504, Qinj_values=Qinj, save_plot=SAVE_PLOT)


#plots for all Qinj values
plot_hits_vs_vth(Qinj_values=Qinj_VALUES, save_plot=SAVE_PLOT)


# In[ ]:


#plot_mean_vs_vth(Qinj=10, column='cal', save_plot=False)
for col in gcu.progressBar(["toa", "tot", "cal"], prefix = '  Plotting Mean values vs Vth:    \t ', suffix = 'Complete', length = 15):
    for Qinj in Qinj_VALUES:
        plot_mean_vs_vth(delay=504, Qinj=Qinj, column=col, save_plot=SAVE_PLOT)


# In[ ]:



for column in ["toa", "tot", "cal"]:
    plot_mean_vs_vth_vs_Qinj(column=column, plot_errorbars=True, save_plot=SAVE_PLOT)


# In[ ]:

for col in gcu.progressBar(["toa", "tot", "cal"], prefix = '  Plotting Std Dev values vs Vth:\t ', suffix = 'Complete', length = 15):
#for column in ["toa", "tot", "cal"]:
    plot_stdDev_vs_vth_vs_Qinj(column=col, save_plot=SAVE_PLOT)


# In[ ]:

for Qinj in gcu.progressBar(Qinj_VALUES, prefix = '  Plotting TOA vs TOT hist2D:    \t ', suffix = 'Complete', length = 15):
#for Qinj in Qinj_VALUES:
    plot_hist2D_TOA_vs_TOT(Qinj_values=Qinj, save_plot=SAVE_PLOT)


# In[ ]:


if MAKE_GIF:
    for dirpath, dirnames, filenames in os.walk(output_folder):
        for dirname in dirnames[:]:  # Create a copy to avoid modifying while iterating
            if dirname.lower() == 'gif':
                gif_folder = os.path.join(dirpath, dirname)
                png_files = [f for f in os.listdir(gif_folder) if f.lower().endswith('.png')]

                # Group PNG files based on their common prefixes
                file_groups = {}
                for png_file in png_files:
                    prefix = png_file.split("_Qinj")[0]
                    if prefix not in file_groups:
                        file_groups[prefix] = []
                    file_groups[prefix].append(os.path.join(gif_folder, png_file))

                # Create GIFs for each group of PNG files
                for prefix, files in file_groups.items():
                    gif_path = os.path.join(gif_folder[:-4], f'{prefix}.gif')
                    gcu.images_to_gif(files, gif_path, duration=0.5)

                # Delete the png files and the "gif" subdirectory after creating the GIFs
                print (f" Erasing {gif_folder}")
                for png_file in png_files:
                    os.remove(os.path.join(gif_folder, png_file))
                os.rmdir(gif_folder)

input("\n  Press Enter to exit...")
print("  Bye! :)\n")

