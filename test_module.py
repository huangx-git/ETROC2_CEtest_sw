from tamalero.ETROC import ETROC
from tamalero.ETROC_Emulator import ETROC2_Emulator as software_ETROC2
from tamalero.DataFrame import DataFrame
from tamalero.utils import get_kcu
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.PixelMask import PixelMask
from tamalero.colors import red, green, yellow
from tamalero.Module import Module
from tamalero.FIFO import FIFO

import numpy as np
from scipy.optimize import curve_fit
from tqdm import tqdm
import pandas as pd
import os
import sys
import json
import time
import datetime
from yaml import load, dump
import traceback

import hist
import matplotlib.pyplot as plt
import mplhep as hep
plt.style.use(hep.style.CMS)

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def run(ETROC, N, fifo=None):
    # currently uses the software ETROC to produce fake data
    if ETROC.isfake:
        return ETROC2.run(N)
    else:
        fifo.send_l1a(N)
        return fifo.pretty_read(None, raw=True)


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
        bounds=([-np.inf,-np.inf],[0,np.inf])
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


def vth_scan(ETROC2, vth_min=693, vth_max=709, vth_step=1, decimal=False, fifo=None, absolute=False):
    N_l1a    =  3200 # how many L1As to send
    vth_min  =   vth_min # scan range
    vth_max  =   vth_max
    if not decimal:
        vth_step =   ETROC2.DAC_step # step size
    else:
        vth_step = vth_step
    N_steps  = int((vth_max-vth_min)/vth_step)+1 # number of steps
    N_pix    = 16*16 # total number of pixels

    vth_axis    = np.linspace(vth_min, vth_max, N_steps)
    run_results = np.empty([N_steps, N_pix])
    
    for vth in vth_axis:
        print(f"Working on threshold {vth=}")
        if decimal:
            ETROC2.wr_reg('DAC', int(vth), broadcast=True)
            #print("Acc value", ETROC2.get_ACC(row=0, col=0)) #doesn't work here
        else:
            ETROC2.set_Vth_mV(vth)
        i = int((vth-vth_min)/vth_step)
        run_results[i] = parse_data(run(ETROC2, N_l1a, fifo=fifo), N_pix)
        
    # transpose so each 1d list is for a pixel & normalize
    if absolute:
        run_results = run_results.transpose()
    else:
        run_results = run_results.transpose()/N_l1a
    return [vth_axis.tolist(), run_results.tolist()]

def vth_scan_internal(ETROC2, row=0, col=0, dac_min=0, dac_max=500, dac_step=1):
    N_steps  = int((dac_max-dac_min)/dac_step)+1 # number of steps
    dac_axis = np.linspace(dac_min, dac_max, N_steps)

    ETROC2.setup_accumulator(row, col)
    results = []
    for i in range(dac_min, dac_max+1, dac_step):
        results.append(
            etroc.check_accumulator(DAC=i, row=row, col=col)
        )
    run_results = np.array(results)
    return [dac_axis, run_results]

def setup(args):
    kcu = get_kcu(args.kcu, control_hub=True, host=args.host, verbose=False)
    if (kcu == 0):
    	# if not basic connection was established the get_kcu function returns 0
    	# this would cause the RB init to fail.
    	sys.exit(1)

    rb_0 = ReadoutBoard(0, kcu=kcu, config=args.configuration)
    data = 0xabcd1234
    kcu.write_node("LOOPBACK.LOOPBACK", data)
    if (data != kcu.read_node("LOOPBACK.LOOPBACK")):
        print("No communications with KCU105... quitting")
        sys.exit(1)      

    is_configured = rb_0.DAQ_LPGBT.is_configured()
    if not is_configured:
        print("RB is not configured, exiting.")
        exit(0)
        
    # FIXME the below code is still pretty stupid
    modules = []
    connected_modules = []

    for i in [1,2,3]:
    	# FIXME we might want to hard reset all ETROCs at this point?
        moduleid = int(args.moduleid) if i==int(args.module) else (i+200)
        m_tmp = Module(rb=rb_0, i=i, enable_power_board=args.enable_power_board, moduleid = moduleid)
        modules.append(m_tmp)
        if m_tmp.ETROCs[0].is_connected():  # NOTE assume that module is connected if first ETROC is connected
            connected_modules.append(i)
            for e_tmp in m_tmp.ETROCs:
                if args.hard_reset:
                    print(f"Running hard reset and default config on module {i}")
                    e_tmp.reset(hard=True)
                    e_tmp.default_config()
                    time.sleep(1.1)
                    #e_tmp.default_config()
                    #
                print("Setting ETROCs into workMode 0")
                e_tmp.wr_reg("workMode", 0, broadcast=True)
                
         #Make sure all ETROCs are turned off 
		
    print(f"Found {len(connected_modules)} connected modules")
    if int(args.module) > 0:
        module = int(args.module)
    else:
        module = connected_modules[0]

    print(f"Will proceed with testing Module {module}")
    print("Module status:")
    modules[module-1].show_status()

    if args.hard_reset:
        for etroc in modules[module-1].ETROCs:
            etroc.reset(hard=True)
            etroc.default_config()

      
    print('Using the following ETROCs: ', args.etrocs)
    etrocs = []
    masks = []
    for i in args.etrocs:
        etroc = modules[module-1].ETROCs[i]
        if args.mode == 'single':
            print(f"Setting the ETROC in single port mode ('right')")
            etroc.set_singlePort("right")
            etroc.set_mergeTriggerData("separate")
        elif args.mode == 'dual':
            print(f"Setting the ETROC in dual port mode ('both')")
            etroc.set_singlePort("both")
            etroc.set_mergeTriggerData("merge")
        masked_pixels = []
        if not args.pixel_masks[i] == 'None':
            mask = PixelMask.from_file(args.pixel_masks[i])
            masked_pixels = mask.get_masked_pixels()

            print(f"\n - Will apply the following pixel mask to ETROC {i}:")
            mask.show()
        etrocs.append(etroc)
        masks.append(masked_pixels)
    return rb_0, module, etrocs, masks
      
def auto_threshold_scan(etroc, args):
    print ("\n - Using auto-threshold calibration for individual pixels")
    print ("Info: if progress is slow, probably most pixel threshold calibrations time out because of high noise levels.")
    baseline = np.empty([16, 16])
    noise_width = np.empty([16, 16])
    with tqdm(total=256, bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as pbar:
        for pixel in range(256):
            row = pixel & 0xF
            col = (pixel & 0xF0) >> 4
            baseline[row][col], noise_width[row][col] = etroc.auto_threshold_scan(row=row, col=col, broadcast=False)
            pbar.update()

    print ("Done with threshold scan")
    fig, ax = plt.subplots(1,1,figsize=(7,7))
    cax = ax.matshow(baseline)
    ax.set_ylabel(r'$Row$')
    ax.set_xlabel(r'$Column$')
    fig.colorbar(cax,ax=ax)
    name = 'baseline_auto_individual'
    fig.savefig(os.path.join(result_dir, "{}.pdf".format(name)))
    fig.savefig(os.path.join(result_dir, "{}.png".format(name)))

    fig, ax = plt.subplots(1,1,figsize=(7,7))
    cax = ax.matshow(noise_width)
    ax.set_ylabel(r'$Row$')
    ax.set_xlabel(r'$Column$')
    fig.colorbar(cax,ax=ax)
    name = 'noisewidth_auto_individual'
    fig.savefig(os.path.join(result_dir, "{}.pdf".format(name)))
    fig.savefig(os.path.join(result_dir, "{}.png".format(name)))

    with open(f'{result_dir}/thresholds.yaml', 'w') as f:
        dump((baseline+noise_width).tolist(), f)
    with open(f'{out_dir}/baselines.yaml', 'w') as f:
    	dump((baseline).tolist(), f)
    with open(f'{out_dir}/noisewidths.yaml', 'w') as f:
    	dump((noise_width).tolist(), f)
    	
    
    return (baseline+noise_width).tolist()
    
def manual_threshold_scan(etroc, fifo, rb_0, args):
    # Prescanning a random pixel to get an idea of the threshold
    row = 4
    col = 3

    elink, slave = etroc.get_elink_for_pixel(row, col)

    rb_0.reset_data_error_count()
    print("\n - Running simple threshold scan on single pixel")
    print(f"Found this pixel on elink {elink}, lpGBT is servant: {slave}")
    vth     = []
    count   = []

    rb_0.get_link_status(elink, slave=slave)

    print("Coarse scan to find the peak location")
    first_val = 1023
    for i in range(0, 1000, 3):
        etroc.wr_reg("DAC", i, row=row, col=col)
        fifo.send_l1a(2000)
        vth.append(i)
        data_cnt = rb_0.read_data_count(elink, slave=slave)
        count.append(data_cnt)
        if data_cnt > 0:
            print(i, data_cnt)
            first_val = i
        rb_0.reset_data_error_count()
        if i > (first_val + 10):
            # break the loop early because this scan is sloooow
            print("I've seen enough, breaking coarse scan.")
            break

    vth_a = np.array(vth)
    count_a = np.array(count)
    vth_max = vth_a[np.argmax(count_a)]
    print(f"Found maximum count at DAC setting vth_max={vth_max}")

    ### threshold scan draft
    dac_min = max(0, vth_max - 75)  # don't run into negatives!
    dac_max = vth_max + 75
    vth_scan_data = vth_scan(
        etroc,
        vth_min = dac_min,
        vth_max = dac_max,
        decimal = True,
        fifo = fifo,
        absolute = True,
    )

    #def plot_scan_results()
    vth_axis    = np.array(vth_scan_data[0])
    hit_rate    = np.array(vth_scan_data[1])
    N_pix       = len(hit_rate) # total # of pixels
    N_pix_w     = int(round(np.sqrt(N_pix))) # N_pix in NxN layout
    max_indices = np.argmax(hit_rate, axis=1)
    maximums    = vth_axis[max_indices]
    max_matrix  = np.empty([N_pix_w, N_pix_w])
    noise_matrix  = np.empty([N_pix_w, N_pix_w])
    threshold_matrix = np.empty([N_pix_w, N_pix_w])

    rawout = {vth_axis[i]:hit_rate.T[i].tolist() for i in range(len(vth_axis))}
    with open(out_dir + '/manual_thresh_scan_data.json', 'w') as f:
        json.dump(rawout, f)

    for pix in range(N_pix):
        r, c = fromPixNum(pix, N_pix_w)
        max_matrix[r][c] = maximums[pix]
        noise_matrix[r][c] = np.size(np.nonzero(hit_rate[pix]))
        max_value = vth_axis[hit_rate[pix]==max(hit_rate[pix])]
        if isinstance(max_value, np.ndarray):
            max_value = max_value[-1]
        zero_dac_values = vth_axis[((vth_axis>(max_value)) & (hit_rate[pix]==0))]
        if len(zero_dac_values)>0:
            threshold_matrix[r][c] = zero_dac_values[0] + 2
        else:
            threshold_matrix[r][c] = dac_max + 2


    # 2D histogram of the mean
    # this is based on the code for automatic sigmoid fits
    # for software emulator data below
    fig, ax = plt.subplots(2,1, figsize=(15,15))
    ax[0].set_title("Peak values of threshold scan")
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
    plt.show()

    plt.close(fig)
    del fig, ax

    fig, ax = plt.subplots()
    plt.title("Thresholds from manual scan")
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
    plt.show()

    plt.close(fig)
    del fig, ax

    with open(f'{result_dir}/thresholds.yaml', 'w') as f:
        dump(threshold_matrix.tolist(), f)
    return threshold_matrix
    
def isolate(etrocs, n):
    for i, e in enumerate(etrocs):
        if i != n:
           e.wr_reg("disDataReadout", 0x1, broadcast=True)

def readout_tests(etroc, masked_pixels, rb_0, args, result_dir = None, out_dir = None):
    etroc.deactivate_hot_pixels(pixels=masked_pixels)
    
    df = DataFrame()
    fifo = FIFO(rb=rb_0)
    
    print("\n - Checking elinks")
    start_time = time.time()
    while True:
        try:
            fifo.reset()
            fifo.send_l1a(10)
            _ = fifo.pretty_read(df)
            fifo.reset()
            break
        except:
            print("Initial (re)set of FIFO.")
            if time.time() - start_time > 1:
                print("FIFO state is unexpected.")
                raise
    etroc.reset()
    
    etroc.wr_reg("DAC", 0, broadcast=True)  # make sure that we're not additionally picking up any noise
    etroc.wr_reg("selfTestOccupancy", 2, broadcast=True)
    etroc.wr_reg("workMode", 0x1, broadcast=True)
    etroc.deactivate_hot_pixels(pixels=masked_pixels)
    etroc.wr_reg("onChipL1AConf", 0x2)  # NOTE: internal L1A is around 1MHz, so we're only turning this on for the shortest amount of time.
    etroc.wr_reg("onChipL1AConf", 0x0)
    test_data = []
    while fifo.get_occupancy() > 0:
        test_data += fifo.pretty_read(df)

    hits_total = np.zeros((16,16))
    row_axis = hist.axis.Regular(16, -0.5, 15.5, name="row", label="row")
    col_axis = hist.axis.Regular(16, -0.5, 15.5, name="col", label="col")
    hit_matrix = hist.Hist(col_axis,row_axis)
    n_events_total = 0
    n_events_hit   = 0
    n_events_err   = 0
    for d in test_data:
        if d[0] == 'trailer':
            n_events_total += 1
            if d[1]['hits'] > 0:
                n_events_hit += 1
        if d[0] == 'data':
            hit_matrix.fill(row=d[1]['row_id'], col=d[1]['col_id'])
            hits_total[d[1]['row_id']][d[1]['col_id']] += 1
            if d[1]['row_id'] != d[1]['row_id2']:
                print("Unpacking error in row ID")
                n_events_err += 1
            if d[1]['col_id'] != d[1]['col_id2']:
                print("Unpacking error in col ID")
                n_events_err += 1
            if d[1]['test_pattern'] != 0xaa:
                print(f"Unpacking error in test pattern, expected 0xAA but got {d[1]['test_pattern']=}")
                n_events_err += 1

    print(f"Got number of total events {n_events_total=}")
    print(f"Events with at least one hit {n_events_hit=}")
    print(f"Events with some error in data unpacking {n_events_err=}")

    fig, ax = plt.subplots(1,1,figsize=(7,7))
    hit_matrix.plot2d(
        ax=ax,
    )
    ax.set_ylabel(r'$Row$')
    ax.set_xlabel(r'$Column$')
    hep.cms.label(
            "ETL Preliminary",
            data=True,
            lumi='0',
            com=0,
            loc=0,
            ax=ax,
            fontsize=15,
        )
    name = 'hit_matrix_internal_test_pattern'
    fig.savefig(os.path.join(result_dir, f"{name}.pdf"))
    fig.savefig(os.path.join(result_dir, f"{name}.png"))

    fifo.reset()
    print("\n - Testing fast command communication - Sending two L1As")
    fifo.send_l1a(2)
    for x in fifo.pretty_read(df):
        print(x)

    #etroc.QInj_unset(broadcast=True)
    fifo.reset()

    print("Will use workMode 1 to get some occupancy (no noise or charge injection)")
    etroc.wr_reg("workMode", 0x1, broadcast=True)  # this overwrites disDataReadout!
    etroc.deactivate_hot_pixels(pixels=masked_pixels)
    #etroc.deactivate_hot_pixels(pixels=[(i,1) for i in range(16)])

    for j in range(1):
        # One go is enough, but can run through this loop many times if there's any issue
        # with FIFO / data readout at any point
        print(j)
        ### Another occupancy map
        i = 0
        occupancy = 0
        print("\n - Will send L1As until FIFO is full.")

        #etroc.QInj_set(30, 0, row=3, col=3, broadcast=False)
        start_time = time.time()
        with tqdm(total=65536, bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as pbar:
            while not fifo.is_full():
                fifo.send_l1a()
                #fifo.send_QInj(delay=j)
                #fifo.send_QInj()
                i +=1
                if i%100 == 0:
                    tmp = fifo.get_occupancy()
                    pbar.update(tmp-occupancy)
                    occupancy = tmp
                #if time.time()-start_time>5:
                #    print("Time out")
                #    break

        test_data = []
        while fifo.get_occupancy() > 0:
            test_data += fifo.pretty_read(df)

        hits_total = np.zeros((16,16))
        hit_matrix = hist.Hist(col_axis,row_axis)
        n_events_total = 0
        n_events_hit   = 0
        for d in test_data:
            if d[0] == 'trailer':
                n_events_total += 1
                if d[1]['hits'] > 0:
                    n_events_hit += 1
            if d[0] == 'data':
                hit_matrix.fill(row=d[1]['row_id'], col=d[1]['col_id'])
                hits_total[d[1]['row_id']][d[1]['col_id']] += 1
                # NOTE could do some CRC check.

        print(f"Got number of total events {n_events_total=}")
        print(f"Events with at least one hit {n_events_hit=}")

        fig, ax = plt.subplots(1,1,figsize=(7,7))
        hit_matrix.plot2d(
            ax=ax,
        )
        ax.set_ylabel(r'$Row$')
        ax.set_xlabel(r'$Column$')
        hep.cms.label(
                "ETL Preliminary",
                data=True,
                lumi='0',
                com=0,
                loc=0,
                ax=ax,
                fontsize=15,
            )
        name = 'hit_matrix_external_L1A'
        fig.savefig(os.path.join(result_dir, "{}.pdf".format(name)))
        fig.savefig(os.path.join(result_dir, "{}.png".format(name)))


        print("\nOccupancy vs column:")
        hit_matrix[{"row":sum}].show(columns=100)
        print("\nOccupancy vs row:")
        hit_matrix[{"col":sum}].show(columns=100)

    # Set the chip back into well-defined workMode 0
    etroc.wr_reg("workMode", 0x0, broadcast=True)
    if args.threshold == 'auto':
        auto_threshold_scan(etroc, args)
    elif args.threshold == "manual":
        manual_threshold_scan(etroc, fifo, args)
    else:
        print(f"Trying to load tresholds from the following file: {args.threshold}")
        with open(args.threshold, 'r') as f:
            threshold_matrix = load(f)

        for row in range(16):
            for col in range(16):
                etroc.wr_reg('DAC', int(threshold_matrix[row][col]), row=row, col=col)
    
    return df, fifo

# initiate
ETROC2 = software_ETROC2()  # currently using Software ETROC2 (fake)
print("ETROC2 emulator instantiated, base configuration successful")
DF = DataFrame('ETROC2')

if __name__ == '__main__':
    # argsparser
    import argparse
    argParser = argparse.ArgumentParser(description = "Argument parser")
    
    #Setup Options
    argParser.add_argument('--configuration', action='store', default='modulev0', choices=['modulev0', 'modulev0b', 'multimodule'], help="Board configuration to be loaded")
    argParser.add_argument('--kcu', action='store', default='192.168.0.10', help="IP Address of KCU105 board")
    argParser.add_argument('--host', action='store', default='localhost', help="Hostname for control hub")
    argParser.add_argument('--module', action='store', default=0, choices=['1','2','3'], help="Module to test")
    argParser.add_argument('--enable_power_board', action='store_true', help="Enable Power Board (all modules). Jumpers must still be set as well.")
    argParser.add_argument('--moduleid', action='store', default=0, help="")
    argParser.add_argument('--multi', action='store_true', help="Run multiple modules at once (for data taking only!)")
    argParser.add_argument('--etrocs', action = 'store', nargs = '*', type = int, default = [0], help = 'ETROC to use on a multi-ETROC module')
    argParser.add_argument('--all-etrocs', action = 'store', type = int, default = 0, help = 'ETROC to use on a multi-ETROC module')

    #Task Set
    argParser.add_argument('--test_chip', action='store_true', default=False, help="Test simple read/write functionality for real chip?")
    
    #run options
    argParser.add_argument('--hard_reset', action='store_true', help="")
    argParser.add_argument('--mode', action='store', default='dual', choices=['dual', 'single'], help="Port mode for ETROC2")
    argParser.add_argument('--skip_sanity_checks', action='store_true', default=False, help="Don't run sanity checks of ETROC2 chip")
    argParser.add_argument('--threshold', action='store', default='auto', help="Use thresholds from manual or automatic scan?")
    argParser.add_argument('--row', action='store', default=4, help="Pixel row to be tested")
    argParser.add_argument('--col', action='store', default=3, help="Pixel column to be tested")
    argParser.add_argument('--pixel_masks', action='store', nargs = '*', default=['None'], help="Pixel mask to apply")
    
    #Charge injection
    argParser.add_argument('--qinj', action='store', default = None, choices = ['simple', 'full'])
    #charges
    #vth_axis
    #pixels
    #nl1a
    
    argParser.add_argument('--config', action='store', default=None, help="config file to use")
    
    args = argParser.parse_args()
    
    
    assert int(args.moduleid)>0, "Module ID is not specified. This is a new feature, please run with --moduleid MODULEID, where MODULEID is the number on the module test board."
    MID = args.moduleid
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
    result_dir = f"results/{MID}/{timestamp}/" #MultiETROC
    out_dir = f"outputs/{MID}/{timestamp}/"
 
    if not os.path.isdir(result_dir):
        os.makedirs(result_dir)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    print(f"Will test module with ID {MID}.") #MultiETROC
    print(f"All results will be stored under timestamp {timestamp}")
    
    if len(args.pixel_masks) == 1 and len(args.etrocs) > 1:
        args.pixel_masks *= len(args.etrocs)
        
    if args.test_chip:
        rb, module, etrocs, masks = setup(args)
        #Check all etrocs off?
        for i in range(len(etrocs)):
            etroc = etrocs[i]
            mask = masks[i]
            etroc.pixel_sanity_check(verbose = args.skip_sanity_checks)
            isolate(etrocs, i)
            df, fifo = readout_tests(etroc, mask, rb, args, result_dir =  result_dir, out_dir = out_dir)
                
            
        
    
    
