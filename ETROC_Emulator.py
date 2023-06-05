# ╔═╗╔═╗╔═╗╔╦╗╦ ╦╔═╗╦═╗╔═╗  ╔═╗╔╦╗╦═╗╔═╗╔═╗╔═╗
# ╚═╗║ ║╠╣  ║ ║║║╠═╣╠╦╝║╣   ║╣  ║ ╠╦╝║ ║║  ╔═╝
# ╚═╝╚═╝╚   ╩ ╚╩╝╩ ╩╩╚═╚═╝  ╚═╝ ╩ ╩╚═╚═╝╚═╝╚═╝

import numpy as np
import os
from crcETROC import mod2div, binstr40
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


maxpixel = 256

class software_ETROC2():
    def __init__(self, BCID=0, verbose=False, chipid=123456, elink=0):
        if verbose:
            print('Initiating fake ETROC2...\n')

        # load ETROC2 dataformat
        with open(os.path.expandvars('$TAMALERO_BASE/configs/dataformat.yaml'), 'r') as f:
            self.format = load(f, Loader=Loader)['ETROC2']

        # load emulated "registers"
        with open(os.path.expandvars('$TAMALERO_BASE/address_table/ETROC2.yaml'), 'r') as f:
            self.regs = load(f, Loader=Loader)

        # storing data for running L1As
        self.data = {
                'elink'     : elink,
                'l1counter' : 0,
                'bcid'      : BCID,
                'type'      : 0,  # use type regular data
                'chipid'    : chipid,
                'status'    : 0,
                'hits'      : 0,
                'crc' : 0,
                'vth'       : 198,
                }
        
        # data from most recent L1A (list of formatted words)
        self.L1Adata = []

        # number of bits in a word
        self.nbits = self.format['nbits']

        # generate fake baseline/noise properties per pixel
        self.bl_means  = [np.random.normal(198, .8) for x in range(maxpixel)]
        self.bl_stdevs = [np.random.normal(  1, .2) for x in range(maxpixel)]


    # emulating I2C connections
    def wr_reg(self, reg, val, pix=None):
        if pix is None:
            self.regs[reg]['value'] = val
        else:
            try:
                self.regs[reg]['value'][pix] = val
            except KeyError:
                self.regs[reg]['value'] = {}
                self.regs[reg]['value'][pix] = val

        # update regs for other pixels if data is shared amongst pixels
        # FIXME I honestly don't know what this does...
        # The whole pixel business needs restructuring
        regcfg = reg.split('Cfg')
        if (len(regcfg) > 1) and (regcfg[1] in [0, 1, 2]):
            for r in range(16):
                for c in range(16):
                    newreg = 'PixR%dC%dCfg%d'%(r,c,regcfg)
                    self.regs[newreg] = val

        return None

    def rd_reg(self, reg, pix=None):
        if pix is None:
            return self.regs[reg]['value']
        else:
            return self.regs[reg]['value'][pix]


    # add hit data to self.L1Adata & increment hit counter
    def add_hit(self,pix):
        matrix_w = int(round(np.sqrt(maxpixel))) # pixels in NxN matrix
        
        # generate random data
        data = {
                'ea'     : 0,
                'row_id' : pix%matrix_w,
                'col_id' : int(np.floor(pix/matrix_w)),
                'toa'    : np.random.randint(0,500),
                'cal'    : np.random.randint(0,500),
                'tot'    : np.random.randint(0,500),
                }
        # format data 
        word = self.format['identifiers']['data']['frame']
        for datatype in data:
            word = ( word +
                ((data[datatype]<<self.format['data']['data'][datatype]['shift'])
                &self.format['data']['data'][datatype]['mask']) )

        if self.data['hits'] < 255:
            # the data format does not allow us to actually have 256 hits
            # so we always have to cut the last one if there would be 100% occupancy
            self.L1Adata.append(word)

            # inc Nhits
            self.data['hits'] += 1

        return None


    # run one L1A
    def runL1A(self):
        self.data['hits'] = 0
        self.L1Adata = [] # wipe previous L1A data
        self.data['l1counter'] += 1

        for pix in range(maxpixel):
            # produce random hit
            val = np.random.normal(self.bl_means[pix], self.bl_stdevs[pix]) 
            # if we have a hit
            if val > self.data['vth'] :
                self.add_hit(pix)
        
        data = self.get_data()
        return data
    

    # run N L1As and return all data from them
    def run(self, N):
        data = []
        for i in range(N):
            self.runL1A()
            data += self.get_data()
        return data


    # return full data package (list of words) for most recent L1A
    def get_data(self):
        # form header word
        header = self.format['identifiers']['header']['frame']
        for datatype in ['l1counter', 'type', 'bcid']:
            header = ( header +
                ((self.data[datatype]<<self.format['data']['header'][datatype]['shift'])
                &self.format['data']['header'][datatype]['mask']) )

        # form trailer word
        trailer = self.format['identifiers']['trailer']['frame']
        for datatype in ['chipid', 'status', 'hits', 'crc']:
            trailer = ( trailer +
                ((self.data[datatype]<<self.format['data']['trailer'][datatype]['shift'])
                &self.format['data']['trailer'][datatype]['mask']) )

        frame= [header] + self.L1Adata + [trailer]

        #Computing CRC and adding it to the trailer
        poly='100101111' #crc generator polynomial
        merged_frames = "".join(binstr40(frame)) #joining the event frames into 1 string of bits
        crc_val = mod2div(merged_frames,poly) #compute CRC value
        frame[-1] = trailer +int(crc_val,2) #Overwrite the trailer content adding the CRC 
        
        return frame