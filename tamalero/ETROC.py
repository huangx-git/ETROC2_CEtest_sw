"""
For ETROC control
"""

from ETROC_Emulator import software_ETROC2
import os
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

class ETROC():

    def __init__(self, write=None, read=None, usefake=True):
        self.usefake = usefake
        if usefake:
            self.fakeETROC = software_ETROC2()
        elif write == None or read == None:
            raise Exception("Pass in write&read functions for ETROC class!")

        with open(os.path.expandvars('$TAMALERO_BASE/address_table/ETROC2.yaml'), 'r') as f:
            self.regs = load(f, Loader=Loader)

    # read & write using register addresses
    def wr_adr(self, adr, val):
        if self.usefake:
            self.fakeETROC.I2C_write(adr, val)
        return None

    def rd_adr(self, adr):
        if self.usefake:
            return self.fakeETROC.I2C_read(adr)
        return None

    # read & write using register name & pix num
    def wr_reg(self, reg, pix, val):
        adr = self.regs[reg]['regadr'][pix]
        mask = self.regs[reg]['mask']
        shift = self.regs[reg]['shift']

        # for some registers, data is stored in two adrs
        if type(adr) is list:
            # get the lengths of parts that we care about in each adr
            lens = [bin(mask[i]).count("1") for i in range(len(adr))]
            # split val into two parts
            vals = [val>>lens[1], val&(2**lens[0]-1)]
            for i in range(len(adr)):
                orig_val = self.rd_adr(adr[i])
                new_val = ((vals[i]<<shift[i])&mask[i]) | (orig_val&(~mask[i]))
                self.wr_adr(adr[i], new_val)
        else:
            orig_val = self.rd_adr(adr)
            new_val = ((val<<shift)&mask) | (orig_val&(~mask))
            self.wr_adr(adr, new_val)

    def rd_reg(self, reg, pix):
        adr = self.regs[reg]['regadr'][pix]
        mask = self.regs[reg]['mask']
        shift = self.regs[reg]['shift']
        # for some registers, data is stored in two adrs
        if type(adr) is list:
            lens = [bin(mask[i]).count("1") for i in range(len(adr))]
            vals = [(self.rd_adr(adr[i])&mask[i]) >> shift[i] for i in range(len(adr))]
            return (vals[0] << lens[1]) | vals[1]
        else:
            return (self.rd_adr(adr)&mask) >> shift

    # (FOR ALL PIXELS) select load capacitance of preamp first stage
    # 0, 80, 80, or 160 fC FIXME typo? 80 appears twice in doc
    def select_Cload(self, C):
        val = {0:0b00, 40:0b01, 80:0b10, 160:0b11}
        try:
            self.wr_reg('CLsel', 1, val(C))
        except KeyError:
            print('Capacitance should be 0, 80, 80, or 160 fC.')
    
    # (FOR ALL PIXELS) select bias current
    # I1 > I2 > I3 > I4
    def select_Ibias(self, i):
        val = [0b000, 0b001, 0b011, 0b111]
        try:
            self.wr_reg('IBsel', 1, val[i])
        except IndexError:
            print('Select between 1 ~ 4.')

    # (FOR ALL PIXELS) select feedback resistance
    # 20, 10, 5.7 or 4.4 kOhm
    def select_Rfeedback(self, R):
        val = {20:0b00, 10:0b00, 5.7:0b10, 4.4:0b11}
        try:
            self.wr_reg('RfSel', 1, val(R))
        except KeyError:
            print('Resistance should be 20, 10, 5.7, or 4.4 kOhms')

    # (FOR ALL PIXELS) select hysteresis voltage
    # Vhys1 > Vhys2 > Vhys3 > Vhys4 > Vhys5 = 0
    def select_Vhys(self, i):
        val = [0b0000, 0b0001, 0b0011, 0b0111, 0b1111]
        try:
            self.wr_reg('HysSel', 1, val(i))
        except IndexError:
            print('Select between 1 ~ 5.')

    # (FOR ALL PIXELS) Power down DAC & discriminator
    def power_down_DACDiscri(self):
        self.wr_reg('PD_DACDiscri', 1, 1)

    # (FOR ALL PIXELS) select injected charge
    # 1 ~ 36 fC, typical charge is 7fC
    def select_Qinj(self, C):
        if C > 32:
            raise Exception('Injected charge should be < 32 fC.')
        self.wr_reg('QSel', 1, C-1)

    # enable charge injection
    def enable_QInj(self, pix):
        self.wr_reg('QInjEn', pix, 1)

    # TDC control
    def autoReset_TDC(self, pix):
        self.wr_reg('autoReset_TDC', pix, 1)

    def enable_TDC(self, pix):
        self.wr_reg('enable_TDC', pix, 1)

    def disable_TDC(self, pix):
        self.wr_reg('enable_TDC', pix, 0)

    def level_TDC(self, pix, w):
        if w > 0b011:
            raise Exception('bit width can be up to 0b011.')
        self.wr_reg('level_TDC', pix, w)

    def reset_TDC(self, pix):
        self.wr_reg('resetn_TDC', pix, 1) #FIXME reg name has typo in doc?

    def enable_TDC_testMode(self, pix):
        self.wr_reg('testMode_TDC', pix, 1)

    def disable_TDC_testMode(self, pix):
        self.wr_reg('testMode_TDC', pix, 0)

    # threshold callibration
    def bypass_THCal(self, pix):
        self.wr_reg('Bypass_THCal', pix, 1)

    def apply_THCal(self, pix):
        self.wr_reg('Bypass_THCal', pix, 0)

    def DAC(self, pix):
        return # FIXME: not sure what this does

    def set_THoffset(self, pix, V):
        self.wr_reg('TH_offset', pix, V)

    def reset_THCal(self, pix):
        self.wr_reg('RSTn_THCal', pix, 1)

    def init_THCal(self, pix): #FIXME better name?
        self.wr_reg('ScanStart_THCal', pix, 1)

    def enable_THCal_buffer(self, pix):
        self.wr_reg('BufEn_THCal', pix, 1)

    def disable_THCal_buffer(self, pix):
        self.wr_reg('BufEn_THCal', pix, 0)

    def enable_THCal_clock(self, pix):
        self.wr_reg('CLKEn_THCal', pix, 1)

    def disable_THCal_clock(self, pix):
        self.wr_reg('CLKEn_THCal', pix, 0)

    def select_workMode(self, pix, mode):
        val = {'normal': 0b00, 'self test fixed': 0b01, 'self test random': 0b10}
        try:
            self.wr_reg('workMode', pix, val(mode))
        except KeyError:
            print('Choose between \'normal\', \'self test fixed\', \'self test random\'.')

    def set_L1Adelay(self, pix, delay):
        self.wr_reg('L1Adelay', pix, delay)

    def enable_data_readout(self, pix):
        self.wr_reg('disDataReadout', pix, 0)

    def disable_data_readout(self, pix):
        self.wr_reg('disDataReadout', pix, 1)

    def enable_trigger_readout(self, pix):
        self.wr_reg('disTrigPath', pix, 0)

    def disable_trigger_readout(self, pix):
        self.wr_reg('disTrigPath', pix, 1)

    def set_trigger_TH(self, pix, datatype, upper=None, lower=None):
        if datatype not in ['TOA', 'TOT', 'Cal']:
            raise Exception('type of data should be TOA, TOT or CAL.')
        if upper is not None:
            self.wr_reg('upper'+data+'Trig', pix, upper)
        if lower is not None:
            self.wr_reg('lower'+data+'Trig', pix, lower)

    def set_data_TH(self, pix, datatype, upper=None, lower=None):
        if datatype not in ['TOA', 'TOT', 'Cal']:
            raise Exception('type of data should be TOA, TOT or CAL.')
        if upper is not None:
            self.wr_reg('upper'+data, pix, upper)
        if lower is not None:
            self.wr_reg('lower'+data, pix, lower)

    def enable_adr_offset(self, pix):
        self.wr_reg('addrOffset', pix, 1)

    def disable_adr_offset(self, pix):
        self.wr_reg('addrOffset', pix, 0)

    def set_selftest_occupancy(self, pix, occ):
        self.wr_reg('selfTestOccupancy', pix, occ)



    def set_vth(self, vth):
        self.fakeETROC.data['vth'] = vth
        print("Vth set to %f."%vth)
