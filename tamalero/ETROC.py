"""
For ETROC control
"""

from ETROC_Emulator import software_ETROC2
from tamalero.colors import red, green
import os
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

class ETROC():

    def __init__(
            self,
            rb=None,
            master='lpgbt',
            i2c_adr=0x72,
            i2c_channel=0,
            elink=0,
            usefake=False,
            verbose=False,
            strict=True,
    ):
        self.usefake = usefake
        if usefake:
            self.fakeETROC = software_ETROC2(elink=elink)
            self.connected = True
            self.master = "software"
            self.i2c_channel = "0"
            self.elink = elink
            self.ver = "23-2-23"  # yy-mm-dd
        else:
            self.I2C_master = rb.DAQ_LPGBT if master == 'lpgbt' else rb.SCA
            self.master = master
            self.rb = rb
            # check if connected
            self.i2c_channel = i2c_channel
            self.i2c_adr = i2c_adr
            self.elink = elink
            self.connected = self.I2C_read(0x13)
            if self.connected:
                self.ver = self.get_ver()
            else:
                self.ver = "X-X-X"

        with open(os.path.expandvars('$TAMALERO_BASE/address_table/ETROC2.yaml'), 'r') as f:
            self.regs = load(f, Loader=Loader)

        self.get_elink_status()
        if usefake:
            for reg in self.regs:
                if isinstance(self.regs[reg]['regadr'], list):
                    for pix in self.regs[reg]['regadr']:
                        self.fakeETROC.wr_reg(reg, self.regs[reg]['default'], pix)
                else:
                    self.fakeETROC.wr_reg(reg, self.regs[reg]['default'], pix=None)

        try:
            self.default_config()
        except TimeoutError:
            if verbose:
                print("Warning: ETROC default configuration failed!")
            pass

        if strict:
            self.consistency(verbose=verbose)

    # =========================
    # === UTILITY FUNCTIONS ===
    # =========================
    def I2C_write(self, adr=0x0, val=0x0):
        if self.usefake:
            raise NotImplementedError("I2C read not implemented for software ETROC")
        else:
            self.I2C_master.I2C_write(
                reg=adr,  # NOTE bad naming, change?
                val=val,
                master=self.i2c_channel,
                slave_addr=self.i2c_adr,
            )

    def I2C_read(self, adr=0x0):
        if self.usefake:
            raise NotImplementedError("I2C read not implemented for software ETROC")
        else:
            return self.I2C_master.I2C_read(
                reg=adr,
                master=self.i2c_channel,
                slave_addr=self.i2c_adr,
            )

    # read & write using register name & pix num
    def wr_reg(self, reg, val, pix=None):
        if self.usefake:
            self.fakeETROC.wr_reg(reg, val)
        else:
            if pix is None:
                adr = self.regs[reg]['regadr']
            else:
                adr = self.regs[reg]['regadr'][pix]
            mask = self.regs[reg]['mask']
            shift = self.regs[reg]['shift']

            # check for data overflow
            if type(adr) is list:
                # get the lengths of parts that we care about in each adr
                lens = [bin(mask[i]).count("1") for i in range(len(adr))]
                masklength = sum(lens)
            else:
                masklength = bin(mask).count("1")
            vallength = len(bin(val)) - 2
            if vallength > masklength:
                print('Overflow warning! Trying to store %s in %d-bit long register %s'%(bin(val), masklength, reg))

            # for some registers, data is stored in two adrs
            if isinstance(adr, list):
                # split val into two parts
                vals = [val>>lens[1], val&(2**lens[0]-1)]
                for i in range(len(adr)):
                    orig_val = self.I2C_read(adr[i])
                    new_val = ((vals[i]<<shift[i])&mask[i]) | (orig_val&(~mask[i]))
                    self.I2C_write(adr[i], new_val)
            else:
                orig_val = self.I2C_read(adr)
                new_val = ((val<<shift)&mask) | (orig_val&(~mask))
                self.I2C_write(adr, new_val)

    def rd_reg(self, reg, pix=None):
        if self.usefake:
            return self.fakeETROC.rd_reg(reg, pix=pix)
        else:
            if pix is None:
                adr = self.regs[reg]['regadr']
            else:
                adr = self.regs[reg]['regadr'][pix]
            mask = self.regs[reg]['mask']
            shift = self.regs[reg]['shift']
            # for some registers, data is stored in two adrs
            if type(adr) is list:
                lens = [bin(mask[i]).count("1") for i in range(len(adr))]
                vals = [(self.I2C_read(adr[i])&mask[i]) >> shift[i] for i in range(len(adr))]
                return (vals[0] << lens[1]) | vals[1]
            else:
                return (self.I2C_read(adr)&mask) >> shift

    def runL1A(self):
        if not self.usefake:
            raise NotImplementedError("Can't send L1As for individual ETROCs / hardware emulators")
        else:
            return self.fakeETROC.runL1A()

    # ============================
    # === MONITORING FUNCTIONS ===
    # ============================

    def get_elink_status(self):
        if self.usefake:
            self.trig_locked = True
            self.daq_locked = True
        else:
            locked = self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.ETROC_LOCKED").value()
            locked_slave = self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.ETROC_LOCKED_SLAVE").value()
            self.trig_locked = ((locked_slave >> self.elink) & 1) == True
            self.daq_locked = ((locked >> self.elink) & 1) == True
        return self.daq_locked, self.trig_locked

    def get_ver(self):
        try:
            ver = [hex(self.I2C_read(i))[2:] for i in [0x19,0x18,0x17]]
            return "-".join(ver)
        except:
            return "--"

    def consistency(self, verbose=False):
        if self.usefake:
            return True
        daq, trig = self.get_elink_status()
        if daq:
            self.wr_reg('disScrambler', 0x0)
            daq1, trig1 = self.get_elink_status()
            self.wr_reg('disScrambler', 0x1)
            assert daq != daq1, "Links and I2C configuration are inconsistent, please check"
            self.get_elink_status()
        else:
            if verbose:
                print("Could not check consistency because link is not ready.")
                print(f"{self.master}, {self.i2c_channel}, {self.elink}")
        return True

    def show_occupancy(self):
        # this needs to be connected to a FIFO read - FIXME
        print ('┏' + 16*'━' + '┓')
        for i in range(16):
            print ('┃'+16*'X'+'┃')
        print ('┗' + 16*'━' + '┛')

    def show_status(self):
        self.get_elink_status()
        print("┏" + 31*'━' + "┓")
        if self.usefake:
            print("┃{:^31s}┃".format("ETROC Software Emulator"))
        else:
            print("┃{:^31s}┃".format("ETROC Hardware Emulator"))
            print("┃{:^31s}┃".format(f"{self.master} channel {self.i2c_channel}"))
            print("┃{:^31s}┃".format(f"address: {hex(self.i2c_adr)}"))
        print("┃{:^31s}┃".format("version: "+self.ver))
        print("┃" + 31*" " + "┃")
        print("┃{:^31s}┃".format(f"Link: {self.elink}"))
        print ('┃' + (green('{:^31s}'.format('DAQ')) if self.daq_locked else red('{:^31s}'.format('DAQ'))) + '┃' )
        print ('┃' + (green('{:^31s}'.format('Trigger')) if self.trig_locked else red('{:^31s}'.format('Trigger'))) + '┃' )

        print("┗" + 31*"━" + "┛")
    # =========================
    # === CONTROL FUNCTIONS ===
    # =========================

    def default_config(self):
        if self.connected:
            self.wr_reg('singlePort', 0)
            self.wr_reg('mergeTriggerData', 0)
            self.wr_reg('disScrambler', 1)

    # *** IN-PIXEL CONFIG ***

    # (FOR ALL PIXELS) set/get load capacitance of preamp first stage
    # 0, 80, 80, or 160 fC FIXME typo? 80 appears twice in doc
    def set_Cload(self, C):
        val = {0:0b00, 40:0b01, 80:0b10, 160:0b11}
        try:
            self.wr_reg('CLsel', val(C), 0)
        except KeyError:
            print('Capacitance should be 0, 80, 80, or 160 fC.')

    def get_Cload(self):
        val = {0b00:0, 0b01:40, 0b10:80, 0b11:160}
        return val[self.rd_reg('CLsel', 0)]

    # (FOR ALL PIXELS) set/get bias current
    # I1 > I2 > I3 > I4
    def set_Ibias(self, i):
        val = {1:0b000, 2:0b001, 3:0b011, 4:0b111}
        try:
            self.wr_reg('IBsel', 0, val[i])
        except KeyError:
            print('Select between 1 ~ 4.')

    def get_Ibias(self):
        val = {0b000:'I1', 0b001:'I2', 0b011:'I3', 0b111:'I4'}
        return val[self.rd_reg('IBSel', 0)]

    # (FOR ALL PIXELS) set/get feedback resistance
    # 20, 10, 5.7 or 4.4 kOhm
    def set_Rfeedback(self, R):
        val = {20:0b00, 10:0b00, 5.7:0b10, 4.4:0b11}
        try:
            self.wr_reg('RfSel', 0, val(R))
        except KeyError:
            print('Resistance should be 20, 10, 5.7, or 4.4 kOhms')

    def get_Rfeedback(self):
        val = {0b00:20, 0b00:10, 0b10:5.7, 0b11:4.4}
        return val[self.rd_reg('RfSel', 0)]

    # (FOR ALL PIXELS) set/get hysteresis voltage
    # Vhys1 > Vhys2 > Vhys3 > Vhys4 > Vhys5 = 0
    def set_Vhys(self, i):
        val = [0b0000, 0b0001, 0b0011, 0b0111, 0b1111]
        try:
            self.wr_reg('HysSel', 0, val(i))
        except IndexError:
            print('Select between 1 ~ 5.')

    def get_Vhys(self):
        val = {0b0000:1, 0b0001:2, 0b0011:3, 0b0111:4, 0b1111:5}
        return val[self.rd_reg('HysSel', 0)]

    # (FOR ALL PIXELS) Power up/down DAC & discriminator
    def power_up_DACDiscri(self):
        self.wr_reg('PD_DACDiscri', 0, 0)

    def power_down_DACDiscri(self):
        self.wr_reg('PD_DACDiscri', 0, 1)

    # (FOR ALL PIXELS) set/get injected charge
    # 1 ~ 36 fC, typical charge is 7fC
    def set_Qinj(self, C):
        if C > 32:
            raise Exception('Injected charge should be < 32 fC.')
        self.wr_reg('QSel', 0, C-1)

    def get_Qinj(self):
        return self.rd_reg('QSel', 0)+1

    # enable/disable charge injection
    def enable_Qinj(self, pix):
        self.wr_reg('QInjEn', pix, 1)

    def disable_Qinj(self, pix):
        self.wr_reg('QInjEn', pix, 0)

    # TDC control
    def autoReset_TDC(self, pix):
        self.wr_reg('autoReset_TDC', pix, 1)

    def enable_TDC(self, pix):
        self.wr_reg('enable_TDC', pix, 1)

    def disable_TDC(self, pix):
        self.wr_reg('enable_TDC', pix, 0)

    def set_level_TDC(self, pix, w):
        if w > 0b011:
            raise Exception('bit width can be up to 0b011.')
        self.wr_reg('level_TDC', pix, w)

    def get_level_TDC(self, pix):
        return self.rd_reg('level_TDC', pix)

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

    def set_Vth_pix(self, pix, vth):
        self.wr_reg('DAC', vth, pix)

    def set_Vth_pix_mV(self, pix, vth):
        if self.usefake:
            self.fakeETROC.data['vth'] = vth
            print("Vth set to %f."%vth)
        else:
            v = vth # FIXME: convert from mV to bit representation
            self.wr_reg('DAC', vth, pix)

    def get_Vth_pix(self, pix):
        self.rd_reg('DAC', pix)

    def get_Vth_pix_mV(self, pix):
        vth = self.rd_reg('DAC', pix)
        # FIXME: convert from bit to mV representation
        return vth

    def set_Vth(self, vth):
        for pix in range(256):
            self.set_Vth_pix(self, pix, vth)

    def set_Vth_mV(self, vth):
        if self.usefake:
            self.fakeETROC.data['vth'] = vth
            print("Vth set to %f."%vth)
        else:
            for pix in range(256):
                self.set_Vth_pix_mV(self, pix, vth)

    # return vth value if vth for all pixels are same;
    # return None if they are not all the same
    def get_Vth(self):
        vth = self.rd_reg('DAC', 0)
        for pix in range(1, 256):
            vth2 = self.rd_reg('DAC', pix)
            if not(vth == vth2):
                return None
        return vth

    def get_Vth_mV(self):
        vth = self.get_Vth
        if vth == None:
            return None
        else:
            return vth # FIXME: convert from bit to mV representation

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

    def set_workMode(self, pix, mode):
        val = {'normal': 0b00, 'self test fixed': 0b01, 'self test random': 0b10}
        try:
            self.wr_reg('workMode', pix, val(mode))
        except KeyError:
            print('Choose between \'normal\', \'self test fixed\', \'self test random\'.')

    def get_workMode(self, pix):
        val = {0b00:'normal', 0b01:'self test fixed', 0b10:'self test random'}
        return val[self.wr_reg('workMod', pix)]

    def set_L1Adelay(self, pix, delay):
        self.wr_reg('L1Adelay', pix, delay)

    def get_L1Adelay(self, pix):
        return self.rd_reg('L1Adelay', pix)

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

    def get_trigger_TH(self, pix, datatype):
        if datatype not in ['TOA', 'TOT', 'Cal']:
            raise Exception('type of data should be TOA, TOT or CAL.')
        upper = 'upper'+data+'Trig'
        lower = 'lower'+data+'Trig'
        return self.rd_reg(upper, pix), self.rd_reg(lower, pix)

    def set_data_TH(self, pix, datatype, upper=None, lower=None):
        if datatype not in ['TOA', 'TOT', 'Cal']:
            raise Exception('type of data should be TOA, TOT or CAL.')
        if upper is not None:
            self.wr_reg('upper'+data, pix, upper)
        if lower is not None:
            self.wr_reg('lower'+data, pix, lower)

    def get_data_TH(self, pix, datatype):
        if datatype not in ['TOA', 'TOT', 'Cal']:
            raise Exception('type of data should be TOA, TOT or CAL.')
        upper = 'upper'+data
        lower = 'lower'+data
        return self.rd_reg(upper, pix), self.rd_reg(lower, pix)

    def enable_adr_offset(self, pix):
        self.wr_reg('addrOffset', pix, 1)

    def disable_adr_offset(self, pix):
        self.wr_reg('addrOffset', pix, 0)

    def set_selftest_occupancy(self, pix, occ):
        self.wr_reg('selfTestOccupancy', pix, occ)

    def get_selftest_occupancy(self, pix):
        return self.rd_reg('selfTestOccupancy', pix)


    # *** IN-PIXEL STATUS ***

    def get_ACC(self, pix):
        return self.rd_reg('ACC', pix)

    def is_scanDone(self, pix):
        result = self.rd_reg('ScanDone', pix)
        if result == 1:
            return True
        else:
            return False

    def get_baseline(self, pix):
        return self.rd_reg('BL', pix)

    def get_noisewidth(self, pix):
        return self.rd_reg('NW', pix)

    def get_threshold(self, pix):
        return self.rd_reg('TH', pix)

    def get_THstate(self, pix):
        return self.rd_reg('THstate', pix)

    def get_pixelID(self, pix):
        return self.rd_reg('PixelID', pix)
