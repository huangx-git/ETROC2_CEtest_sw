from tamalero.RegParser import RegParser
import os
import sys
import pickle
import copy
import random
import json
import tamalero.colors as colors
from tamalero.utils import read_mapping, chunk
from time import sleep
from datetime import datetime

from tamalero.lpgbt_constants import LpgbtConstants

class LPGBT(RegParser):

    def __init__(self, rb=0, trigger=False, flavor='small', master=None, kcu=None):
        '''
        Initialize lpGBT for a certain readout board number (rb).
        The trigger lpGBT is accessed through I2C of the master (= DAQ lpGBT).
        '''
        self.nodes = {}
        self.rb = rb
        self.trigger = trigger
        if self.trigger:
            assert isinstance(master, LPGBT), "Trying to initialize a trigger lpGBT but got no lpGBT master."
            self.master = master
        self.LPGBT_CONST = LpgbtConstants()
        self.adc_mapping = read_mapping(os.path.expandvars('$TAMALERO_BASE/configs/LPGBT_mapping.yaml'), 'adc')

        if kcu != None:
            self.kcu = kcu

        try:
            self.callibrate_adc()
        except:
            print("Need to callibrate ADC in the future. Use default values for now.")
            self.cal_gain = 1.85
            self.cal_offset = 512

        # check if kcu is dummy
        if kcu != None and self.kcu.hw != None:
            try:
                self.ver = self.rd_adr(0x005).value() >> 7
            except AttributeError:
                print ("cannot load lpgbt version; load after connecting to kcu.")
        else:
            # if dummy, just parse v0 for now
            self.ver = 0

    def link_status(self, verbose=False):
        if self.trigger:
            print ("Checking trigger link status")
            if verbose:
                print ("Uplink ready:", self.kcu.read_node("READOUT_BOARD_%i.LPGBT.TRIGGER.UPLINK.READY"%self.rb).value()==1 )
                print ("FEC count:", self.kcu.read_node("READOUT_BOARD_%i.LPGBT.TRIGGER.UPLINK.FEC_ERR_CNT"%self.rb).value())
            return (
                (self.kcu.read_node("READOUT_BOARD_%i.LPGBT.TRIGGER.UPLINK.FEC_ERR_CNT"%self.rb).value() == 0) &
                (self.kcu.read_node("READOUT_BOARD_%i.LPGBT.TRIGGER.UPLINK.READY"%self.rb).value() == 1)
            )
        else:
            print ("Checking DAQ link status")
            if verbose:
                print ("Uplink ready:", self.kcu.read_node("READOUT_BOARD_%i.LPGBT.DAQ.UPLINK.READY"%self.rb).value()==1 )
                print ("FEC count:", self.kcu.read_node("READOUT_BOARD_%i.LPGBT.DAQ.UPLINK.FEC_ERR_CNT"%self.rb).value())
            return (
                (self.kcu.read_node("READOUT_BOARD_%i.LPGBT.DAQ.UPLINK.FEC_ERR_CNT"%self.rb).value() == 0) &
                (self.kcu.read_node("READOUT_BOARD_%i.LPGBT.DAQ.UPLINK.READY"%self.rb).value() == 1)
            )
    
    def get_version(self):
        self.ver = self.rd_adr(0x005).value() >> 7

    def reset_tx_mgt_by_mask(self, mask):
        id = "MGT.MGT_TX_RESET"
        self.kcu.write_node(id, mask)

    def reset_rx_mgt_by_mask(self, mask):
        id = "MGT.MGT_RX_RESET"
        self.kcu.write_node(id, mask)

    def reset_trigger_mgts(self):
        id = "MGT.MGT_RX_RESET"
        # trigger links on 1,3,5,7,9
        self.kcu.write_node(id, 0x2aa)
        self.kcu.write_node(id, 0x000)

    def reset_daq_mgts(self):

        for id in ["MGT.MGT_RX_RESET", "MGT.MGT_TX_RESET"]:
            # daq links on 0,2,4,6,8
            self.kcu.write_node(id, 0x155)
            self.kcu.write_node(id, 0x000)

    def init_trigger_links(self):
        if self.trigger:
            lpgbt = self.master
        else:
            lpgbt = self

        id = "LPGBT.RW.TESTING.ULECDATASOURCE"
        node = self.get_node(id)
        self.write_reg(self.master.I2C_write, self.master.I2C_read, node, value=6)
        sleep (0.1)
        self.write_reg(self.master.I2C_write, self.master.I2C_read, node, value=0)
        #lpgbt.I2C_write(reg=0x118, val=6, master=2, slave_addr=0x70)
        #sleep (0.1)
        #lpgbt.I2C_write(reg=0x118, val=0, master=2, slave_addr=0x70)

        self.reset_trigger_mgts()

    def power_up_init(self, verbose=True):
        if not self.trigger:

            # toggle the uplink to and from 40MHz clock, for some reason this is
            # needed for the mgt to lock

            if (not self.kcu.read_node(
                    "READOUT_BOARD_%d.LPGBT.DAQ.UPLINK.READY" % self.rb)):
                print("  > Performing LpGBT Magic...")
                id = "LPGBT.RW.TESTING.ULECDATASOURCE"
                self.wr_reg(id, 6)
                sleep(0.1)
                self.wr_reg(id, 0)
                print("  > Magic Done")
        else:
            # servant lpgbt base configuration
            self.master.program_slave_from_file('configs/config_slave.txt', verbose=verbose)  #FIXME check if we still need this black box after power cycle.

            # toggle the uplink to and from 40MHz clock, for some reason this is
            # needed for the mgt to lock

            self.init_trigger_links()


    def connect_KCU(self, kcu):
        '''
        We need to connect to the KCU somehow
        '''
        self.kcu = kcu

    def align_DAQ(self):
        for i in range(28):
            id = "READOUT_BOARD_%d.LPGBT.DAQ.UPLINK.ALIGN_%d" % (self.rb, i)
            self.kcu.write_node(id, 2)

    def wr_adr(self, adr, data):
        #defer = not self.kcu.auto_dispatch  # if auto dispatch is turned off, keep it off.
        #self.kcu.toggle_dispatch()  # turn off auto dispatch for this transaction
        #self.kcu.write_node("READOUT_BOARD_%d.SC.TX_GBTX_ADDR" % self.rb, 115)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_REGISTER_ADDR" % self.rb, adr)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_DATA_TO_GBTX" % self.rb, data)
        self.kcu.action("READOUT_BOARD_%d.SC.TX_WR" % self.rb)
        self.kcu.action("READOUT_BOARD_%d.SC.TX_START_WRITE" % self.rb)
        #return self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_FROM_GBTX" % self.rb)
        #if not defer:  # turn auto dispatch back on only if it wasn't set to false before
        #    self.kcu.dispatch()
        #self.rd_flush()

    def rd_adr(self, adr):
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_REGISTER_ADDR" % self.rb, adr)
        self.kcu.action("READOUT_BOARD_%d.SC.TX_START_READ" % self.rb)

        valid = self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_VALID" % self.rb).valid()
        if valid:
            return self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_FROM_GBTX" % self.rb)

        print("LpGBT read failed!")
        return None

    def wr_reg(self, id, data):
        node = self.get_node(id)
        if self.trigger:
            self.write_reg(self.master.I2C_write, self.master.I2C_read, node, data)  # inherited from RegParser
        else:
            self.write_reg(self.wr_adr, self.rd_adr, node, data)  # inherited from RegParser

    def rd_reg(self, id):
        node = self.get_node(id)
        if self.trigger:
            data = self.read_reg(self.master.I2C_read, node)  # inherited from RegParser
        else:
            data = self.read_reg(self.rd_adr, node)
        return data

    def rd_flush(self):
        i = 0
        while (not self.kcu.read_node("READOUT_BOARD_%d.SC.RX_EMPTY" % self.rb)):
            self.kcu.action("READOUT_BOARD_%d.SC.RX_RD" % self.rb)
            read = self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_FROM_GBTX" % self.rb)
            i = i + 1

    def configure_gpio_outputs(self, outputs=0x2401, defaults=0x0401):
        # have to first set defaults, then switch to outputs otherwise we reset the VTRx+
        self.wr_reg('LPGBT.RWF.PIO.PIOOUTH', defaults >> 8)
        self.wr_reg('LPGBT.RWF.PIO.PIOOUTL', defaults & 0xFF)
        self.wr_reg('LPGBT.RWF.PIO.PIODIRH', outputs >> 8)
        self.wr_reg('LPGBT.RWF.PIO.PIODIRL', outputs & 0xFF)

    def set_uplink_alignment(self, link, val, quiet=False):
        if self.trigger:
            if not quiet:
                print ("Setting uplink alignment for trigger link %i to %i"%(link, val))
            id = "READOUT_BOARD_%d.LPGBT.TRIGGER.UPLINK.ALIGN_%d" % (self.rb, link)
        else:
            if not quiet:
                print ("Setting uplink alignment for DAQ link %i to %i"%(link, val))
            id = "READOUT_BOARD_%d.LPGBT.DAQ.UPLINK.ALIGN_%d" % (self.rb, link)
        self.kcu.write_node(id, val)

    def get_uplink_alignment(self, link):
        if self.trigger:
            return self.kcu.read_node("READOUT_BOARD_%d.LPGBT.TRIGGER.UPLINK.ALIGN_%d"%(self.rb, link)).value()
        else:
            return self.kcu.read_node("READOUT_BOARD_%d.LPGBT.DAQ.UPLINK.ALIGN_%d"%(self.rb, link)).value()

    def set_uplink_invert(self, link, invert=True):
        # 0x02 - not inverted, 0x0a - inverted. don't actually need those details any more
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX_CHN_CONTROL.EPRX%dINVERT" % link, invert)

    def get_uplink_invert(self, link):
        return self.rd_reg("LPGBT.RWF.EPORTRX.EPRX_CHN_CONTROL.EPRX%dINVERT" % link)

        #if self.trigger:
        #    return self.I2C_read(reg=0xcc+link, master=2, slave_addr=0x70)
        #else:
        #    return self.rd_adr(0xcc+link).value()

    def configure_clocks(self, en_mask, invert_mask=0):
        for i in range(27):
            if 0x1 & (en_mask >> i):
                self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK%dFREQ" % i, 1)
                self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK%dDRIVESTRENGTH" % i, 4)
            if 0x1 & (invert_mask >> i):
                self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK%dINVERT" % i, 1)

    def config_eport_dlls(self):
        print("Configuring eport dlls...")
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLCURRENT", 0x1)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLCONFIRMCOUNT", 0x1)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLFSMCLKALWAYSON", 0x0)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLCOARSELOCKDETECTION", 0x0)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXENABLEREINIT", 0x0)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDATAGATINGENABLE", 0x1)

    def configure_eptx(self):

        for i in range(4):
            # [0x0a7] EPTXDataRate
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX%dDATARATE" % i, 0x3)
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX%dDATARATE" % i, 0x3)
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX%dDATARATE" % i, 0x3)
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX%dDATARATE" % i, 0x3)

        # EPTXxxEnable
        # EPTXxxDriveStrength
        for i in [0, 2, 4, 8, 10, 12]:
            group = str(i//4)
            link = str(i % 4)
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX%s%sENABLE" % (group, link), 0x1)
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX%dDRIVESTRENGTH" % i, 0x3)

        # enable mirror feature
        for i in range(4):
            self.wr_reg("LPGBT.RWF.EPORTTX.EPTX%dMIRRORENABLE" % i, 0x1)

    def configure_eprx(self):

        print("Configuring elink inputs...")
        # Enable Elink-inputs

        # enable inputs
        for i in range(24):
            group = str(i//4)
            link = str(i % 4)
            self.wr_reg("LPGBT.RWF.EPORTRX.EPRX%s%sENABLE" % (group, link), 1)

        for i in range(7):
            # set banks to 320 Mbps (1)
            self.wr_reg("LPGBT.RWF.EPORTRX.EPRX%dDATARATE" % i, 1)
            # set banks to continuous phase tracking (2)
            self.wr_reg("LPGBT.RWF.EPORTRX.EPRX%dTRACKMODE" % i, 2)

        # enable 100 ohm termination
        for i in range(28):
            self.wr_reg("LPGBT.RWF.EPORTRX.EPRX_CHN_CONTROL.EPRX%dTERM" % i, 1)

    def init_adc(self):
        self.wr_reg("LPGBT.RW.ADC.ADCENABLE", 0x1)  # enable ADC
        self.wr_reg("LPGBT.RW.ADC.TEMPSENSRESET", 0x1)  # resets temp sensor
        self.wr_reg("LPGBT.RW.ADC.VDDMONENA", 0x1)  # enable dividers
        self.wr_reg("LPGBT.RW.ADC.VDDTXMONENA", 0x1)  # enable dividers
        self.wr_reg("LPGBT.RW.ADC.VDDRXMONENA", 0x1)  # enable dividers
        self.wr_reg("LPGBT.RW.ADC.VDDPSTMONENA", 0x1,)  # enable dividers
        self.wr_reg("LPGBT.RW.ADC.VDDANMONENA", 0x1)  # enable dividers
        self.wr_reg("LPGBT.RWF.CALIBRATION.VREFENABLE", 0x1)  # vref enable
        self.wr_reg("LPGBT.RWF.CALIBRATION.VREFTUNE", 0x63)

    #def read_adcs(self):
    #    self.init_adc()
    #    print("ADC Readings:")
    #    for i in range(16):
    #        name = ""
    #        conv = 0
    #        if (i==0 ): conv=1;      name="VTRX TH1"
    #        if (i==1 ): conv=1/0.55; name="1V4D * 0.55"
    #        if (i==2 ): conv=1/0.55; name="1V5A * 0.55"
    #        if (i==3 ): conv=1/0.33; name="2V5TX * 0.33"
    #        if (i==4 ): conv=1;      name="RSSI"
    #        if (i==5 ): conv=1;      name="N/A"
    #        if (i==6 ): conv=1/0.33; name="2V5RX * 0.33"
    #        if (i==7 ): conv=1;      name="RT1"
    #        if (i==8 ): conv=1;      name="EOM DAC (internal signal)"
    #        if (i==9 ): conv=1/0.42; name="VDDIO * 0.42 (internal signal)"
    #        if (i==10): conv=1/0.42; name="VDDTX * 0.42 (internal signal)"
    #        if (i==11): conv=1/0.42; name="VDDRX * 0.42 (internal signal)"
    #        if (i==12): conv=1/0.42; name="VDD * 0.42 (internal signal)"
    #        if (i==13): conv=1/0.42; name="VDDA * 0.42 (internal signal)"
    #        if (i==14): conv=1;      name="Temperature sensor (internal signal)"
    #        if (i==15): conv=1/0.50; name="VREF/2 (internal signal)"
    #
    #        read = self.read_adc(i)
    #        print("\tch %X: 0x%03X = %f, reading = %f (%s)" % (i, read, read/1024., conv*read/1024., name))

    def read_adcs(self): #read and print all adc values
        self.init_adc()
        adc_dict = self.adc_mapping
        for adc_reg in adc_dict.keys():
            pin = adc_dict[adc_reg]['pin']
            comment = adc_dict[adc_reg]['comment']
            value = self.read_adc(pin)
            input_voltage = value / (2**10 - 1) * adc_dict[adc_reg]['conv']
            out_string = "register: {0}".format(adc_reg).ljust(22)+\
            "pin: {0}".format(pin).ljust(10)+"reading: {0}".format(value).ljust(16)+\
            "in voltage: {0:.4f}".format(input_voltage).ljust(22) + "comment: '{0}'".format(comment)
            print(out_string)

    def read_adc(self, channel):
        # ADCInPSelect[3:0]  |  Input
        # ------------------ |----------------------------------------
        # 4'd0               |  ADC0 (external pin)
        # 4'd1               |  ADC1 (external pin)
        # 4'd2               |  ADC2 (external pin)
        # 4'd3               |  ADC3 (external pin)
        # 4'd4               |  ADC4 (external pin)
        # 4'd5               |  ADC5 (external pin)
        # 4'd6               |  ADC6 (external pin)
        # 4'd7               |  ADC7 (external pin)
        # 4'd8               |  EOM DAC (internal signal)
        # 4'd9               |  VDDIO * 0.42 (internal signal)
        # 4'd10              |  VDDTX * 0.42 (internal signal)
        # 4'd11              |  VDDRX * 0.42 (internal signal)
        # 4'd12              |  VDD * 0.42 (internal signal)
        # 4'd13              |  VDDA * 0.42 (internal signal)
        # 4'd14              |  Temperature sensor (internal signal)
        # 4'd15              |  VREF/2 (internal signal)
    
        self.wr_reg("LPGBT.RW.ADC.ADCINPSELECT", channel)
        self.wr_reg("LPGBT.RW.ADC.ADCINNSELECT", 0xf)
    
        self.wr_reg("LPGBT.RW.ADC.ADCCONVERT", 0x1)
        self.wr_reg("LPGBT.RW.ADC.ADCENABLE", 0x1)

        done = 0
        while (done==0):
            #print ("Waiting")
            done = self.rd_reg("LPGBT.RO.ADC.ADCDONE")
    
        val = self.rd_reg("LPGBT.RO.ADC.ADCVALUEL")
        val |= self.rd_reg("LPGBT.RO.ADC.ADCVALUEH") << 8
    
        self.wr_reg("LPGBT.RW.ADC.ADCCONVERT", 0x0)
        self.wr_reg("LPGBT.RW.ADC.ADCENABLE", 0x1)
    
        return val

    def callibrate_adc(self, recallibrate=False):
        serial_num = self.get_board_id()['lpgbt_serial']
        cal_file = "lpgbt_cal_%d.json"%serial_num
        
        # load from json file if it exists (unless recallibrate)
        if os.path.isfile(cal_file) and not(recallibrate):
            with open(cal_file, 'r') as openfile:
                cal_data = json.load(openfile)
            gain = cal_data['gain']
            offset = cal_data['offset']
            print("Loaded ADC callibration data. Gain: %f / Offset: %d"%(gain, offset))
        
        # else, determine callibration constants
        else:
            # determine offset; both at Vref/2
            offset = self.read_adc(0xf)
            
            # determine gain; one at Vref/2, one at ground
            # use internal grounding - ADC12, supply voltage divider off
            initial_val = self.rd_reg("LPGBT.RW.ADC.VDDMONENA")
            self.wr_reg("LPGBT.RW.ADC.VDDMONENA", 0x0)

            # ADC = (Vdiff/Vref)*Gain*512 + Offset
            gain = 2*abs(self.read_adc(0xC)-offset)/512
            self.wr_reg("LPGBT.RW.ADC.VDDMONENA", initial_val)
            print("Callibrated ADC. Gain: %f / Offset: %d"%(gain, offset))

            # save to json file
            cal_data = {'gain': gain, 'offset': offset}
            with open(cal_file, "w") as outfile:
                json.dump(cal_data, outfile)
                print("Callibration data saved to %s"%cal_file)

        self.cal_gain = gain
        self.cal_offset = offset
        
    def set_dac(self, v_out):
        if v_out > 1.00:
            print ("Can't set the DAC to a value larger than 1.0 V!")
            return
        v_ref = 1.00
        value = min(int(v_out/v_ref*4095), 4095)
        lo_bits = value & 0xFF
        hi_bits = (value & ~lo_bits) >> 8
        self.wr_reg("LPGBT.RWF.CALIBRATION.VREFENABLE", 0x1)  # vref enable
        self.wr_reg("LPGBT.RWF.CALIBRATION.VREFTUNE", 0x63)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEL", lo_bits)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEH", hi_bits)

    def read_dac(self):
        v_ref = 1.00
        lo_bits = self.rd_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEL")
        hi_bits = self.rd_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEH")
        value = lo_bits | (hi_bits << 8)
        return value/4096*v_ref

    def reset_dac(self):
        # reset means: output is set to maximum voltage
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEL", 0x0)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEH", 0x0)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACENABLE", 0x0)
        self.wr_reg("LPGBT.RWF.CALIBRATION.VREFENABLE", 0x0)

    def initialize(self):
        self.wr_reg("LPGBT.RWF.CHIPCONFIG.HIGHSPEEDDATAOUTINVERT", 0x80)

        # turn on clock outputs
        print ("Configuring clocks now.")
        self.configure_clocks(0x0fffffff, 0x0)

        # setup up sca eptx/rx
        # sca_setup() # maybe not needed???

    def loopback(self, nloops=100):
        for i in range(nloops):
            wr = random.randint(0, 255)
            id = "LPGBT.RWF.CHIPID.CHIPID1"
            self.wr_reg(id, wr)
            rd = self.rd_reg(id)
            if wr != rd:
                print("ERR: %d wr=0x%08X rd=0x%08X" % (i, wr, rd))
                return
            if (i % (nloops/100) == 0 and i != 0):
                print("%i reads done..." % i)

    def gpio_init(self, outputs=0x2401):
        self.wr_reg("LPGBT.RWF.PIO.PIODIRH", outputs >> 8)
        self.wr_reg("LPGBT.RWF.PIO.PIODIRL", outputs & 0xFF)

        self.set_gpio(0,1) # GBT_RESET_B
        self.set_gpio(10,1) # VTRX RESET_B
        self.set_gpio(13,0) # VTRX DIS

    def set_gpio(self, ch, val):
        if (ch > 7):
            node = "LPGBT.RWF.PIO.PIOOUTH"
            ch = ch - 8
        else:
            node = "LPGBT.RWF.PIO.PIOOUTL"

        reg = self.get_node(node)
        adr = reg.address
        rd = self.rd_adr(adr)
        
        if val == 0:
            rd = rd & (0xff ^ (1 << ch))
        else:
            rd = rd | (1 << ch)

        self.wr_adr(adr, rd)

    def reset_pattern_checkers(self):
    
        self.kcu.action("READOUT_BOARD_%i.LPGBT.PATTERN_CHECKER.RESET" % self.rb)
    
        for link in (0, 1):
            prbs_en_id = "READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.CHECK_PRBS_EN_%d" % (self.rb, link)
            upcnt_en_id = "READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.CHECK_UPCNT_EN_%d" % (self.rb, link)
            self.kcu.write_node(prbs_en_id, 0)
            self.kcu.write_node(upcnt_en_id, 0)
    
            self.kcu.write_node(prbs_en_id, 0x00FFFFFF)
            self.kcu.write_node(upcnt_en_id, 0x00FFFFFF)
    
        self.kcu.action("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.CNT_RESET" % self.rb)
    
    
    def read_pattern_checkers(self, quiet=False, log=True, log_dir="./tests/"):
        if log_dir and os.path.isfile(log_dir + "pattern_checks.p") and log:
            log_dict = pickle.load(open(log_dir + "pattern_checks.p", "rb"))
        elif log:
            default_dict = {key:{"error":[], "total_frames":[]} for key in range(24)}
            link_dict = {"PRBS":copy.deepcopy(default_dict), "UPCNT":copy.deepcopy(default_dict)}
            log_dict = {"Link 0":copy.deepcopy(link_dict), "Link 1":copy.deepcopy(link_dict)}

        for link in (0, 1):
    
            prbs_en = self.kcu.read_node("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.CHECK_PRBS_EN_%d" % (self.rb, link))
            upcnt_en = self.kcu.read_node("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.CHECK_UPCNT_EN_%d" % (self.rb, link))
    
            prbs_errs = 28*[0]
            upcnt_errs = 28*[0]
    
            for mode in ["PRBS", "UPCNT"]:
                if quiet is False:
                    print("Link " + str(link) + " " + mode + ":")
                for i in range(28):
    
                    check = False
    
                    if mode == "UPCNT" and ((upcnt_en >> i) & 0x1):
                        check = True
                    if mode == "PRBS" and ((prbs_en >> i) & 0x1):
                        check = True
    
                    if check:
                        self.kcu.write_node("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.SEL" % (self.rb), link*28+i)
    
                        uptime_msbs = self.kcu.read_node("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.TIMER_MSBS" % (self.rb))
                        uptime_lsbs = self.kcu.read_node("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.TIMER_LSBS" % (self.rb))
    
                        uptime = (uptime_msbs << 32) | uptime_lsbs
    
                        errs = self.kcu.read_node("READOUT_BOARD_%d.LPGBT.PATTERN_CHECKER.%s_ERRORS" % (self.rb, mode))
    
                        if quiet is False:
                            s = "    Channel %02d %s bad frames of %s (%.0f Gb)" % (i, ("{:.2e}".format(errs)), "{:.2e}".format(uptime), uptime*8/1000000000.0)
                            if (errs == 0):
                                s += " (ber <%s)" % ("{:.1e}".format(1/(uptime*8)))
                                print(colors.green(s))
                            else:
                                s += " (ber>=%s)" % ("{:.1e}".format((1.0*errs)/uptime))
                                print(colors.red(s))
    
                        if mode == "UPCNT":
                            upcnt_errs[i] = errs
                        if mode == "PRBS":
                            prbs_errs[i] = errs
                        if log:
                            log_dict["Link {}".format(link)][mode][i]["error"].append(int(errs))
                            log_dict["Link {}".format(link)][mode][i]["total_frames"].append(int(uptime))
    
                    else:
                        if mode == "UPCNT":
                            upcnt_errs[i] = 0xFFFFFFFF
                        if mode == "PRBS":
                            prbs_errs[i] = 0xFFFFFFFF
        if log and log_dir:
            pickle.dump(log_dict, open(log_dir + "pattern_checks.p", "wb"))
        return log_dict

    def set_uplink_group_data_source(self, type, pattern=0x55555555):
        setting = 0
        if (type == "normal"):
            setting = 0
        elif(type == "prbs7"):
            setting = 1
        elif(type == "cntup"):
            setting = 2
        elif(type == "cntdown"):
            setting = 3
        elif(type == "pattern"):
            setting = 4
        elif(type == "invpattern"):
            setting = 5
        elif(type == "loopback"):
            setting = 6
        else:
            print("Setting invalid in set_uplink_group_data_source")
            return
        
        for i in range(7):
            self.wr_reg("LPGBT.RW.TESTING.ULG%dDATASOURCE"%i, setting)
    
        if (setting == 4 or setting == 5):
            for i in range(4):
                self.wr_reg("LPGBT.RW.TESTING.DPDATAPATTERN%d"%i, 0xff&(pattern >> (i*8)))

    def set_downlink_data_src(self, source):
        id = "READOUT_BOARD_%d.LPGBT.DAQ.DOWNLINK.DL_SRC" % self.rb
        if (source == "etroc"):
            self.kcu.write_node(id, 0)
        if (source == "upcnt"):
            self.kcu.write_node(id, 1)
        if (source == "prbs"):
            self.kcu.write_node(id, 2)

    def set_ps0_phase(self, phase):
        phase = phase & 0x1ff
        msb = 0x1 & (phase >> 8)
        self.wr_reg("LPGBT.RWF.PHASE_SHIFTER.PS0ENABLEFINETUNE", 1)
        self.wr_reg("LPGBT.RWF.PHASE_SHIFTER.PS0DELAY_7TO0", 0xff & phase)
        self.wr_reg("LPGBT.RWF.PHASE_SHIFTER.PS0DELAY_8", msb)

    def I2C_write(self, reg=0x0, val=10, master=2, slave_addr=0x70, adr_nbytes=2, freq=2, ignore_response=False):
        '''
        reg: target register
        val: has to be a single byte, or a list of single bytes.
        master: lpGBT master (2 by default)
        this function is following https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#example-2-multi-byte-write
        '''

        if ignore_response and False:
            self.kcu.toggle_dispatch()

        i2cm     = 2
        OFFSET_WR = i2cm*(self.LPGBT_CONST.I2CM1CMD - self.LPGBT_CONST.I2CM0CMD) #shift the master by 2 registers (we can change this)
        OFFSET_RD = i2cm*(self.LPGBT_CONST.I2CM1STATUS - self.LPGBT_CONST.I2CM0STATUS)

        adr_bytes = [ ((reg >> (8*i)) & 0xff) for i in range(adr_nbytes) ]

        if type(val == int):
            data_bytes = [val]
        elif type(val == list):
            data_bytes = val
        else:
            raise("data must be an int or list of ints")

        nbytes = len(adr_bytes+data_bytes)

        self.wr_adr(
            self.LPGBT_CONST.I2CM0DATA0+OFFSET_WR,
            nbytes<<self.LPGBT_CONST.I2CM_CR_NBYTES_of | freq<<self.LPGBT_CONST.I2CM_CR_FREQ_of,
        )
        self.wr_adr(
            self.LPGBT_CONST.I2CM0CMD+OFFSET_WR,
            self.LPGBT_CONST.I2CM_WRITE_CRA,
        )
        
        for i, data_byte in enumerate(adr_bytes+data_bytes):
            page    = int(i/4)
            offset  = int(i%4)

            self.wr_adr(
                self.LPGBT_CONST.I2CM0DATA0 + OFFSET_WR + offset,
                data_byte
            )

            if i%4==3 or i==(nbytes-1):
                self.wr_adr(
                    self.LPGBT_CONST.I2CM0CMD+OFFSET_WR,
                    self.LPGBT_CONST.I2CM_W_MULTI_4BYTE0+page,
                )

        self.wr_adr(self.LPGBT_CONST.I2CM0ADDRESS+OFFSET_WR, slave_addr)# write the address of the follower
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_MULTI)# execute write (c)

        if not ignore_response:
            status = self.rd_adr(self.LPGBT_CONST.I2CM0STATUS+OFFSET_RD)
            retries = 0
            while (status != self.LPGBT_CONST.I2CM_SR_SUCC_bm):
                status = self.rd_adr(self.LPGBT_CONST.I2CM0STATUS+OFFSET_RD)
                #if (status & self.LPGBT_CONST.I2CM_SR_LEVEERR_bm):
                #    print ("The SDA line is pulled low before initiating a transaction")
                #if (status & self.LPGBT_CONST.I2CM_SR_NOACK_bm):
                #    print("The I2C transaction was not acknowledged by the I2C slave")
                retries += 1
                if retries > 50:
                    print ("Write not successfull!")
                    break

    def I2C_read(self, reg=0x0, master=2, slave_addr=0x70, nbytes=1, adr_nbytes=2, freq=2, quiet=False):
        #https://gitlab.cern.ch/lpgbt/pigbt/-/blob/master/backend/apiapp/lpgbtLib/lowLevelDrivers/MASTERI2C.py#L83
        i2cm      = master
	
        # we can also switch to sth like this:
        # i2cm1cmd = self.get_node('LPGBT.RW.I2C.I2CM1CMD').real_address

        OFFSET_WR = i2cm*(self.LPGBT_CONST.I2CM1CMD - self.LPGBT_CONST.I2CM0CMD) #using the offset trick to switch between masters easily
        OFFSET_RD = i2cm*(self.LPGBT_CONST.I2CM1STATUS - self.LPGBT_CONST.I2CM0STATUS)
    
        #adr = []
        #for i in range(adr_nbytes): 
        #    adr.append((reg >> (8*i)) & 0xff)

        #regl = (int(reg) & 0xFF) >> 0
        #regh = (int(reg)) >> 8

        ################################################################################
        # Write the register address
        ################################################################################

        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-cr-0x0
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA0+OFFSET_WR, adr_nbytes<<self.LPGBT_CONST.I2CM_CR_NBYTES_of | (freq<<self.LPGBT_CONST.I2CM_CR_FREQ_of))
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_CRA) #write to config register
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-w-multi-4byte0-0x8
        for i in range (adr_nbytes): 
            self.wr_adr(getattr(self.LPGBT_CONST, "I2CM0DATA%d"%i) + OFFSET_WR, (reg >> (8*i)) & 0xff )
        # self.wr_adr(self.LPGBT_CONST.I2CM0DATA1 + OFFSET_WR , regh)
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_W_MULTI_4BYTE0) # prepare a multi-write
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-multi-0xc
        self.wr_adr(self.LPGBT_CONST.I2CM0ADDRESS+OFFSET_WR, slave_addr)
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_MULTI)# execute multi-write

        ################################################################################
        # Write the data
        ################################################################################
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-cr-0x0
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA0+OFFSET_WR, nbytes<<self.LPGBT_CONST.I2CM_CR_NBYTES_of | freq<<self.LPGBT_CONST.I2CM_CR_FREQ_of)
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_CRA) #write to config register
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-read-multi-0xd
        self.wr_adr(self.LPGBT_CONST.I2CM0ADDRESS+OFFSET_WR, slave_addr) #write the address of follower first
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_READ_MULTI)# execute read
        
        status = self.rd_adr(self.LPGBT_CONST.I2CM0STATUS+OFFSET_RD)
        retries = 0
        while (status != self.LPGBT_CONST.I2CM_SR_SUCC_bm):
            status = self.rd_adr(self.LPGBT_CONST.I2CM0STATUS+OFFSET_RD)
            #if (status & self.LPGBT_CONST.I2CM_SR_LEVEERR_bm):
            #    print ("The SDA line is pulled low before initiating a transaction")
            #if (status & self.LPGBT_CONST.I2CM_SR_NOACK_bm):
            #    print("The I2C transaction was not acknowledged by the I2C slave")
            retries += 1
            if retries > 50:
                if not quiet:
                    print ("Read not successfull!")
                return None

        read_values = []

        i2cm0read15 = self.LPGBT_CONST.I2CM0READ15
        for i in range(0, nbytes):
            tmp_adr = abs(i-i2cm0read15)+OFFSET_RD
            read_values.append(self.rd_adr(tmp_adr).value())

        #read_value = self.rd_adr(self.LPGBT_CONST.I2CM0READ15+OFFSET_RD) # get the read value. this is just the first byte
        if nbytes==1:
            return read_values[0]  # this is so bad, but needed for compatibility with wr_reg
        else:
            return read_values

    def program_slave_from_file (self, filename, master=2, slave_addr=0x70, verbose=True):
        print("Programming Trigger lpGBT from file.")
        f = open(filename, "r")
        for line in f:
            adr, data = line.split(" ")
            adr = int(adr)
            wr = int(data.replace("0x",""), 16)
            if (wr != 0):
                if verbose:
                    print("Writing address: %d, value: 0x%02x" % (adr, wr))
                self.I2C_write(reg=adr, val=wr, master=master, slave_addr=slave_addr, ignore_response=True)
                #rd = self.I2C_read(reg=adr, master=master, slave_addr=slave_addr)
                #if (wr!=rd):
                #    print("LPGBT readback error 0x%02X != 0x%02X at adr %d" % (wr, rd, adr))
        self.kcu.dispatch()

    def read_temp_i2c(self):
        res = self.I2C_read(reg=0x0, master=1, slave_addr=0x48, nbytes=2)
        temp_dig = (res[0] << 4) + (res[1] >> 4)
        return temp_dig*0.0625

    def get_board_id(self):
        '''
        |-------+------+---------------+--------------------------------------|
        | Range | Bits | Meaning       | Description                          |
        |-------+------+---------------+--------------------------------------|
        |  15:0 |   16 | Serial Number | Board serial number                  |
        | 31:29 |    3 | Version Major | Major version of RB (e.g. 1 in v1.6) |
        | 28:25 |    4 | Version Minor | Major version of RB (e.g. 6 in v1.6) |
        | 24:23 |    2 | LPGBT Version | 0x0 = v0; 0x1 = v1                   |
        | 22:19 |    4 | Board Flavor  | 0x0 = 3 module; 0x1 =                |
        |-------+------+---------------+--------------------------------------|

        * User IDs
        #+begin_src python :results output
        def user_id (serial, major, minor, lpgbt, flavor):
          data = 0
          data |= serial & 0xffff
          data |= (major & 0x7) << 29
          data |= (minor & 0xf) << 25
          data |= (lpgbt & 0x3) << 23
          data |= (flavor & 0xf) << 19
          return data

        0x003 -> 7:0
        0x002 -> 15:8
        0x001 -> 23:16
        0x000 -> 

        '''

        board_id = {}
        flavors = {0: '3 module', 1: '6 module', 2: '7 module'}

        user_id =   self.rd_reg("LPGBT.RWF.CHIPID.USERID3") << 24 |\
                    self.rd_reg("LPGBT.RWF.CHIPID.USERID2") << 16 |\
                    self.rd_reg("LPGBT.RWF.CHIPID.USERID1") << 8 |\
                    self.rd_reg("LPGBT.RWF.CHIPID.USERID0")
        board_id['rb_ver_major']    = user_id >> 29
        board_id['rb_ver_minor']    = user_id >> 25 & (2**4-1)
        board_id['lpgbt_ver']       = user_id >> 23 & (2**2-1)
        board_id['rb_flavor']       = flavors[user_id >> 19 & (2**4-1)]
        board_id['serial_number']   = user_id & (2**16-1)
        board_id['lpgbt_serial']    = self.get_chip_serial()
        
        return board_id

    def eyescan(self, end_of_count_sel=7):

        self.wr_reg("LPGBT.RW.EOM.EOMENDOFCOUNTSEL", end_of_count_sel)
        self.wr_reg("LPGBT.RW.EOM.EOMENABLE", 1)

        # Equalizer settings
        self.wr_reg("LPGBT.RWF.EQUALIZER.EQCAP", 0x1)
        self.wr_reg("LPGBT.RWF.EQUALIZER.EQRES0", 0x1)
        self.wr_reg("LPGBT.RWF.EQUALIZER.EQRES1", 0x1)
        self.wr_reg("LPGBT.RWF.EQUALIZER.EQRES2", 0x1)
        self.wr_reg("LPGBT.RWF.EQUALIZER.EQRES3", 0x1)

        datavalregh    = "LPGBT.RO.EOM.EOMCOUNTERVALUEH"
        datavalregl    = "LPGBT.RO.EOM.EOMCOUNTERVALUEL"
        eomphaseselreg = "LPGBT.RW.EOM.EOMPHASESEL"
        eomstartreg    = "LPGBT.RW.EOM.EOMSTART"
        eomstatereg    = "LPGBT.RO.EOM.EOMSMSTATE"
        eombusyreg     = "LPGBT.RO.EOM.EOMBUSY"
        eomendreg      = "LPGBT.RO.EOM.EOMEND"
        eomvofsel      = "LPGBT.RW.EOM.EOMVOFSEL"

        cntvalmax = 0
        cntvalmin = 2**20

        ymin=0
        ymax=30
        xmin=0
        xmax=64

        eyeimage = [[0 for x in range(xmin, xmax)] for y in range(ymin, ymax)]

        print("\nRunning eye scan...")
        for y_axis in range(ymin, ymax):

            # update yaxis
            self.wr_reg(eomvofsel, y_axis)

            for x_axis in range(xmin, xmax):

                x_axis_wr = x_axis

                # update xaxis
                self.wr_reg(eomphaseselreg, x_axis_wr)

                # start measurement
                self.wr_reg(eomstartreg, 0x1)

                countervalue = (self.rd_reg(datavalregh)) << 8 | self.rd_reg(datavalregl)
                if (countervalue > cntvalmax):
                    cntvalmax = countervalue
                if (countervalue < cntvalmin):
                    cntvalmin = countervalue
                eyeimage[y_axis][x_axis] = countervalue

                # deassert eomstart bit
                self.wr_reg(eomstartreg, 0x0)

        print("Counter value max=%d\n" % cntvalmax)

        # normalize for plotting and save to file
        normalize = lambda val : int(100*(cntvalmax - val)/(cntvalmax-cntvalmin))
        eye_scan_data = [[normalize(x) for x in y] for y in eyeimage]

        if not os.path.isdir("eye_scan_results"):
            os.mkdir("eye_scan_results")

        serialnums = "lpgbt%s_kcu%s" %(self.get_chip_serial(), self.kcu.get_serial())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = "%s_%s" %(serialnums, timestamp)

        with open("eye_scan_results/%s.json" %filename, "w") as outfile:
            json.dump(eye_scan_data, outfile)
        print("Data saved to eye_scan_results/%s.json\n" %filename)

        # print results to bash
        try:
            from colored import fg, bg, attr
        except:
            print("Need to pip install colored to print out results.")
            print("Eye scan results were still saved and can be plotted.")

        color_scale = [124,196,202,214,190,82,50,38,21,19]
        sys.stdout.write("Color Scale: ")
        for i in range(10):
            sys.stdout.write("%s%01d%s" % (bg(color_scale[i]),i,attr('reset')))
        sys.stdout.write("\n\n")
        
        for y_axis in range(ymin, ymax):
            for x_axis in range(xmin, xmax):
                printval = int(eyeimage[y_axis][x_axis]/1000)
                sys.stdout.write("%s%01d%s" % (bg(color_scale[printval]), printval, attr('reset')))
                sys.stdout.flush()
            sys.stdout.write("\n")

    def get_chip_serial(self):
        return self.rd_reg("LPGBT.RWF.CHIPID.CHIPID3") << 24 |\
               self.rd_reg("LPGBT.RWF.CHIPID.CHIPID2") << 16 |\
               self.rd_reg("LPGBT.RWF.CHIPID.CHIPID1") << 8 |\
               self.rd_reg("LPGBT.RWF.CHIPID.CHIPID0")

    def get_power_up_state_machine(self, quiet=True):
        
        pusmstate = self.rd_reg("LPGBT.RO.PUSM.PUSMSTATE")

        if not quiet:

            print ("PUSM State:")

            if (pusmstate==0):  print ("\t0  = ARESET - the FSM stays in this state when power-on-reset or an external reset (RSTB) is asserted. \n\t When external signal PORdisable is asserted, the signal generated by the internal power-on-reset is ignored. All action flags are reset in this state.")
            if (pusmstate==1):  print ("\t1  = RESET - synchronous reset state. In this state, the FSM produces synchronous reset signal for various circuits. \n\t All action flags are not reset in this state.")
            if (pusmstate==2):  print ("\t2  = WAIT_VDD_STABLE - the FSM waits for VDD to raise. It has fixed duration of 4,000 clock cycles (~100us).")
            if (pusmstate==3):  print ("\t3  = WAIT_VDD_HIGHER_THAN_0V90 - the FSM monitors the VDD voltage. \n\t It waits until VDD stays above 0.9V for a period longer than 1us.\n\t This state is bypassed if PORdisable is active.")
            if (pusmstate==4):  print ("\t4  = FUSE_SAMPLING - initiate fuse sampling.")
            if (pusmstate==5):  print ("\t5  = UPDATE FROM FUSES - transfer fuse values into registers. Transfer executed only if updateEnable fuse in POWERUP2 register is blown.")
            if (pusmstate==6):  print ("\t6  = PAUSE_FOR_PLL_CONFIG - this state is foreseen for initial testing of the chip when optimal registers settings are not yet known and the e-fuses have not been burned. The FSM will wait in this state until pllConfigDone bit is asserted. While in this state, the user can use the I2C interface to write values to the registers. For more details about intended use please refer to Section 3.7.")
            if (pusmstate==7):  print ("\t7  = WAIT_POWER_GOOD - this state is foreseen to make sure that the power supply voltage is stable before proceeding with further initialization. When PGEnable bit is enabled the FSM will wait until VDD level stays above value configured by PGLevel[2:0] for longer than time configured by PGDelay[4:0]. If PGEnable is not set, one can use PGDelay[4:0] as a fixed delay. The PGLevel[2:0] and PGDelay[4:0] are interpreted according to Table 8.1 and Table 8.2.")
            if (pusmstate==8):  print ("\t8  = RESETOUT - in this state a reset signal is generated on the resetout pin. The reset signal is active low. The duration of the reset pulse is controlled by value of ResetOutLength[1:0] field according to Table 8.3.")
            if (pusmstate==9):  print ("\t9  = I2C_TRANS - this state is foreseen to execute one I2C transaction. This feature can be used to configure a laser driver chip or any other component in the system. To enable transaction, the I2CMTransEnable bit has to be programmed and master channel has to be selected by I2CMTransChannel[1:0]. Remaining configuration like I2CMTransAddressExt[2:0], I2CMTransAddress[6:0], and I2CMTransCtrl[127:0] should be configured according to the description in the I2C slaves chapter.")
            if (pusmstate==10): print ("\t10 = RESET_PLL - reset PLL/CDR control logic.")
            if (pusmstate==11): print ("\t11 = WAIT_PLL_LOCK - waits for the PLL/CDR to lock. \n\t When lpGBT is configured in simplex RX or transceiver mode the lock signal comes from frame aligner. \n\t It means that the valid lpGBT frame has to be sent in the downlink. \n\t This state can be interrupted by timeout action (see the description below).")
            if (pusmstate==12): print ("\t12 = INIT_SCRAM - initializes scrambler in the uplink data path.")
            if (pusmstate==13): print ("\t13 = PAUSE_FOR_DLL_CONFIG - this state is foreseen for the case in which user wants to use serial interface (IC/EC) to configure the chip. The FSM will wait in this state until dllConfigDone bit is asserted. While in this state, the user can use the serial interface (IC/EC) or I2C interface to write values to the registers. For more details about intended use please refer to Section 3.7.")
            if (pusmstate==14): print ("\t14 = RESET_DLLS - reset DLLs in ePortRx groups and phase-shifter.")
            if (pusmstate==15): print ("\t15 = WAIT_DLL_LOCK - wait until all DLL report to be locked. This state can be interrupted by timeout action (see the description below).")
            if (pusmstate==16): print ("\t16 = RESET_LOGIC_USING_DLL - reset a logic using DLL circuitry. In case of ePortRx groups, this signal is used to initialize automatic phase training. This state has no impact on a phase-shifter operation.")
            if (pusmstate==17): print ("\t17 = WAIT_CHNS_LOCKED - in this state, FSM waits until automatic phase training is finished for all enabled ePortRx groups. One should keep in mind, that data transitions have to be present on the enabled channels to acquire lock. By default this state is bypassed, it can be enabled asserting PUSMReadyWhenChnsLocked bit in POWERUP register. This state can be interrupted by timeout action (see the description below).")
            if (pusmstate==18): print ("\t18 = READY - initialization is completed. Chip is operational. READY signal is asserted.")

        return pusmstate

    def monitor_pusm(self, maxcount=10000):
        print ("Initial PUSM state:")
        tmp = self.get_power_up_state_machine(quiet=False)
        for i in range(maxcount): 
            pusm = self.get_power_up_state_machine() 
            if not (tmp==pusm): 
                print ("Changed state to:", pusm) 
            tmp = pusm



if __name__ == '__main__':

    lpgbt = LPGBT()
    lpgbt.get_version()
    lpgbt.parse_xml(self.ver)
    lpgbt.dump(nMax=10)
