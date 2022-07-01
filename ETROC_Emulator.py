# ╔═╗╔═╗╔═╗╔╦╗╦ ╦╔═╗╦═╗╔═╗  ╔═╗╔╦╗╦═╗╔═╗╔═╗╔═╗
# ╚═╗║ ║╠╣  ║ ║║║╠═╣╠╦╝║╣   ║╣  ║ ╠╦╝║ ║║  ╔═╝
# ╚═╝╚═╝╚   ╩ ╚╩╝╩ ╩╩╚═╚═╝  ╚═╝ ╩ ╩╚═╚═╝╚═╝╚═╝

import numpy as np
import yaml
import os

maxpixel = 256


# data storage
data_stor = {0x0:   0, # test register
             0x1: 198, # vth
             0x2: [] # accumulator nums
            }

# emulating I2C connections
def I2C_write(reg, val):
    data_stor[reg] = val
    return None

def I2C_read(reg):
    return data_stor[reg]

if not os.path.isfile("dataformat.yaml"):
    raise Exception('missing dataformat.yaml; run update_commands.sh to retrieve')

with open('dataformat.yaml', 'r') as stream:
    dataformat = yaml.safe_load(stream)['ETROC2']

class software_ETROC2():
    def __init__(self, BCID="0x000"):
        print('initiating fake ETROC2...')
        self.BCID = BCID
        self.type = 0  #use type regular data

        self.l1counter  = 0  #cumulative num of L1As requested
        self.hitcounter = np.zeros(maxpixel) #cumulative counter of hits on each pixel
        
        self.L1Adata = [] #data from most recent L1A, including TOT,TOA,CAL vals

        # fake baseline/noise properties per pixel
        self.bl_means  = [np.random.normal(198, .8) for x in range(maxpixel)]
        self.bl_stdevs = [np.random.normal(  1, .2) for x in range(maxpixel)]

    def add_hit(self,pix):
        #dataformat['identifier']['data']['frame']
        #dataformat['data']['data'] # ea, col_id, row_id, toa, cal, tot
        ea = 0 # temp
        
        pix_w = int(round(np.sqrt(maxpixel)))
        row = pix%pix_w
        col = int(np.floor(pix/pix_w))
        
        toa = np.random.randint(0,500)
        cal = np.random.randint(0,500)
        tot = np.random.randint(0,500)
        
        form = dataformat['data']['data']
        self.L1Adata.append(
                 dataformat['identifiers']['data']['frame']
                + (ea  << form['ea']['shift'])
                + (col << form['col_id']['shift'])
                + (row << form['row_id']['shift'])
                + (toa << form['toa']['shift'])
                + (cal << form['cal']['shift'])
                + (tot << form['tot']['shift'])
                )
        print(self.L1Adata)

    def runL1A(self):
        self.L1Adata = [] # wipe previous L1A data
        self.l1counter += 1

        vth = I2C_read(0x1)

        for pix in range(maxpixel):
            # produce random hit
            val = np.random.normal(self.bl_means[pix], self.bl_stdevs[pix]) 
            # if we have a hit
            if val > vth :
                self.hitcounter[pix] += 1
                self.add_hit(pix)

        return self.get_data()

    # return full data package for most recent L1A
    def get_data(self):
        Nhit    = len(self.hitdata)
        header  = "00"+format(0x3555555,'026b')+format(BCID,'012b')
        hitdata = "".join(self.hitdata)
        trailer = "10"+format(0x5555555,'028b')+format(Nhit,'09b')+format(P,'1b')
        return header + hitdata + trailer


# run simulated hits (simplified version)
def runpixel(N, pixel):
    acc_num = 0
    vth = I2C_read(0x1)

    for i in range(N):
        # produce random hit
        val = np.random.normal(bl_means[pixel], bl_stdevs[pixel])
        if val > vth :
            acc_num += 1

    return acc_num

def run(N):
    rundata = [0 for x in range(maxpixel)]
    for pixel in range(maxpixel):
        rundata[pixel] = runpixel(N, pixel)
    I2C_write(0x2, rundata)
    return rundata
