"""
For ETROC control
"""

from tamalero.utils import load_yaml, ffs, bit_count
from tamalero.colors import red, green
import os

here = os.path.dirname(os.path.abspath(__file__))

here = os.path.dirname(os.path.abspath(__file__))

class ETROC():

    def __init__(
            self,
            rb=None,
            master='lpgbt',
            i2c_adr=0x72,
            i2c_channel=0,
            elink=0,
            verbose=False,
            strict=True,
    ):
        self.isfake = False
        self.I2C_master = rb.DAQ_LPGBT if master == 'lpgbt' else rb.SCA
        self.master = master
        self.rb = rb
        # check if connected
        self.i2c_channel = i2c_channel
        self.i2c_adr = i2c_adr
        self.elink = elink
        self.is_connected()
        if self.connected:
            self.ver = self.get_ver()
        else:
            self.ver = "X-X-X"

        self.regs = load_yaml(os.path.join(here, '../address_table/ETROC2_example.yaml'))

        self.get_elink_status()
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
        if self.isfake:
            raise NotImplementedError("I2C read not implemented for software ETROC")
        else:
            self.I2C_master.I2C_write(
                reg=adr,  # NOTE bad naming, change?
                val=val,
                master=self.i2c_channel,
                slave_addr=self.i2c_adr,
            )

    def I2C_read(self, adr=0x0):
        if self.isfake:
            raise NotImplementedError("I2C read not implemented for software ETROC")
        else:
            return self.I2C_master.I2C_read(
                reg=adr,
                master=self.i2c_channel,
                slave_addr=self.i2c_adr,
            )

    def get_adr(self, reg, row=0, col=0, broadcast=False):
        tmp = []
        for address in self.regs[reg]['address']:
            tmp.append(address | \
               row << 5 | \
               col << 9 | \
               broadcast << 13 | \
               self.regs[reg]['stat'] << 14 | \
               self.regs[reg]['pixel'] << 15 )
        return tmp

    def wr_adr(self, adr, val):
        if self.isfake:
            #print ("writing fake")
            self.write_adr(adr, val)
        else:
            self.I2C_write(adr, val)

    def rd_adr(self, adr):
        if self.isfake:
            #print ("reading fake")
            return self.read_adr(adr)
        else:
            return self.I2C_read(adr)

    # read & write using register name & pix num
    def wr_reg(self, reg, val, row=0, col=0, broadcast=False):
        '''
        reg - Register name
        val - value to write
        row - arbitrary value for periphery, 0..15 for in pixel
        col - arbitrary value for periphery, 0..15 for in pixel
        broadcast - True for broadcast to all pixels
        '''
        masks    = self.regs[reg]['mask']
        shifts   = list(map(ffs, masks))
        n_bits   = [0] + list(map(bit_count, masks))
        adr      = self.get_adr(reg, row=row, col=col, broadcast=broadcast)
        if val > 2**(sum(n_bits))-1:
            raise RuntimeError(f"Value {val} is larger than the number of bits of register {reg} allow ({sum(n_bits)})")
        if self.isfake:
            #print(f"writing {adr=}, {value=}")
            adr = self.get_adr(reg, row=row, col=col, broadcast=False)
            if broadcast:
                for row in range(16):
                    for col in range(16):
                        self.wr_reg(reg, val, row=row, col=col, broadcast=False)

        for i, a in enumerate(adr):
            read = self.rd_adr(a)
            value = (((val >> n_bits[i]) << shifts[i]) & masks[i]) | (read & ~masks[i])
            self.wr_adr(a, value)


    def rd_reg(self, reg, row=0, col=0):
        '''
        reg - Register name
        val - value to write
        row - arbitrary value for periphery, 0..15 for in pixel
        col - arbitrary value for periphery, 0..15 for in pixel
        '''
        masks    = self.regs[reg]['mask']
        shifts   = list(map(ffs, masks))
        n_bits   = [0] + list(map(bit_count, masks))

        adr = self.get_adr(reg, row=row, col=col)
        tmp = 0
        for i, a in enumerate(adr):
            read = (self.rd_adr(a) & masks[i]) >> shifts[i]
            tmp |= (read << n_bits[i])
        return tmp

    # ============================
    # === MONITORING FUNCTIONS ===
    # ============================

    def is_connected(self):
        self.connected = self.I2C_read(0x0)  # read from first register (default value 0x2C)
        return self.connected

    def get_elink_status(self):
        if self.isfake:
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
        if self.isfake:
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
        if self.isfake:
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
    def set_Cload(self, C, row=0, col=0, broadcast=True):
        val = {0:0b00, 40:0b01, 80:0b10, 160:0b11}
        try:
            self.wr_reg('CLsel', val(C), row=row, col=col, broadcast=broadcast)
        except KeyError:
            print('Capacitance should be 0, 80, 80, or 160 fC.')

    def get_Cload(self, row=0, col=0):
        val = {0b00:0, 0b01:40, 0b10:80, 0b11:160}
        return val[self.rd_reg('CLsel', row=row, col=col)]

    # (FOR ALL PIXELS) set/get bias current
    # I1 > I2 > I3 > I4
    def set_Ibias(self, i, row=0, col=0, broadcast=True):
        val = {1:0b000, 2:0b001, 3:0b011, 4:0b111}
        try:
            self.wr_reg('IBsel', val[i], row=row, col=col, broadcast=broadcast)
        except KeyError:
            print('Select between 1 ~ 4.')

    def get_Ibias(self, row=0, col=0):
        val = {0b000:'I1', 0b001:'I2', 0b011:'I3', 0b111:'I4'}
        return val[self.rd_reg('IBSel', row=row, col=col)]

    # (FOR ALL PIXELS) set/get feedback resistance
    # 20, 10, 5.7 or 4.4 kOhm
    def set_Rfeedback(self, R, row=0, col=0, broadcast=True):
        val = {20:0b00, 10:0b00, 5.7:0b10, 4.4:0b11}
        try:
            self.wr_reg('RfSel', val(R), row=row, col=col, broadcast=broadcast)
        except KeyError:
            print('Resistance should be 20, 10, 5.7, or 4.4 kOhms')

    def get_Rfeedback(self, row=0, col=0):
        val = {0b00:20, 0b00:10, 0b10:5.7, 0b11:4.4}
        return val[self.rd_reg('RfSel', row=row, col=col)]

    # (FOR ALL PIXELS) set/get hysteresis voltage
    # Vhys1 > Vhys2 > Vhys3 > Vhys4 > Vhys5 = 0
    def set_Vhys(self, i, row=0, col=0, broadcast=True):
        val = [0b0000, 0b0001, 0b0011, 0b0111, 0b1111]
        try:
            self.wr_reg('HysSel', val(i), row=row, col=col, broadcast=broadcast)
        except IndexError:
            print('Select between 1 ~ 5.')

    def get_Vhys(self, row=0, col=0):
        val = {0b0000:1, 0b0001:2, 0b0011:3, 0b0111:4, 0b1111:5}
        return val[self.rd_reg('HysSel', row=row, col=col)]

    # (FOR ALL PIXELS) Power up/down DAC & discriminator
    def power_up_DACDiscri(self, row=0, col=0, broadcast=True):
        self.wr_reg('PD_DACDiscri', 0, row=row, col=col, broadcast=broadcast)

    def power_down_DACDiscri(self, row=0, col=0):
        self.wr_reg('PD_DACDiscri', 1, row=row, col=col)

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

    def set_Vth_mV(self, vth, row=0, col=0, broadcast=True):
        # FIXME this needs to be understood
        # Pretend that we set the threshold and then the "DAC" register
        # sets the threshold in offset_step/2**10 steps?
        offset_step = (1000/2**6)
        th_step = offset_step/2**10
        offset = int(vth/offset_step)
        residual = vth - offset*offset_step
        th = round(residual/th_step)
        self.wr_reg('TH_offset', offset, row=row, col=col, broadcast=broadcast)
        self.wr_reg('DAC', th, row=row, col=col, broadcast=broadcast)
        #if self.usefake:
        #    self.fakeETROC.data['vth'] = vth
        #    print("Vth set to %f."%vth)
        #else:
        #    v = vth # FIXME: convert from mV to bit representation
        #    self.wr_reg('DAC', vth, pix)

    def get_Vth_mV(self, row=0, col=0):
        offset_step = (1000/2**6)
        th_step = offset_step/2**10
        offset = self.rd_reg('TH_offset', row=row, col=col)
        th = self.rd_reg('DAC', row=row, col=col)
        return offset*offset_step + th*th_step

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
