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
    def __init__(self, BCID=0):
        print('initiating fake ETROC2...')
        self.bcid = BCID
        self.type = 0  #use type regular data
        self.chipid = 0
        self.status = 0
        self.crc = 0

        self.l1counter  = 0  #cumulative num of L1As requested
        self.hitcounter = np.zeros(maxpixel) #cumulative counter of hits on each pixel

        self.L1Adata = [] #data from most recent L1A, including TOT,TOA,CAL vals

        self.nbits = dataformat['nbits']

        # fake baseline/noise properties per pixel
        self.bl_means  = [np.random.normal(198, .8) for x in range(maxpixel)]
        self.bl_stdevs = [np.random.normal(  1, .2) for x in range(maxpixel)]

    def add_hit(self,pix):
        ea = 0 # temp
        
        pix_w = int(round(np.sqrt(maxpixel)))
        row = pix%pix_w
        col = int(np.floor(pix/pix_w))
        
        toa = np.random.randint(0,500)
        cal = np.random.randint(0,500)
        tot = np.random.randint(0,500)
        
        df = dataformat['data']['data']
        self.L1Adata.append(
                 dataformat['identifiers']['data']['frame']
                + ((ea  << df['ea']['shift'])&df['ea']['mask'])
                + ((col << df['col_id']['shift'])&df['col_id']['mask'])
                + ((row << df['row_id']['shift'])&df['row_id']['mask'])
                + ((toa << df['toa']['shift'])&df['toa']['mask'])
                + ((cal << df['cal']['shift'])&df['cal']['mask'])
                + ((tot << df['tot']['shift'])&df['tot']['mask'])
                )

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
    
    def run(self, N):
        data = []
        for i in range(N):
            self.runL1A()
            data.append(self.get_data)
        return data

    # return full data package for most recent L1A
    def get_data(self):
        df_h = dataformat['data']['header']
        df_t = dataformat['data']['trailer']
        
        header = (dataformat['identifiers']['header']['frame']
                + ((self.l1counter << df_h['l1counter']['shift'])&df_h['l1counter']['mask'])
                + ((self.type << df_h['type']['shift'])&df_h['type']['mask'])
                + ((self.bcid << df_h['bcid']['shift'])&df_h['bcid']['mask']) )
        
        trailer = (dataformat['identifiers']['trailer']['frame']
                + ((self.chipid << df_t['chipid']['shift'])&df_t['chipid']['mask'])
                + ((self.status << df_t['status']['shift'])&df_t['status']['mask'])
                + ((len(self.L1Adata) << df_t['hits']['shift'])&df_t['hits']['mask'])
                + ((self.crc << df_t['crc']['shift'])&df_t['crc']['mask']) )

        # assemble
        data = header
        for hit in self.L1Adata:
            data = (data << self.nbits) + hit
        data = (data << self.nbits) + trailer
        
        return data


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
