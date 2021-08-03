from tamalero.RegParser import RegParser
import os
import pickle
import copy
import random
import tamalero.colors as colors
from time import sleep

from tamalero.lpgbt_constants import LpgbtConstants

class LPGBT(RegParser):

    def __init__(self, rb=0, trigger=False, flavor='small', master=None):
        '''
        Initialize lpGBT for a certain readout board number (rb).
        The trigger lpGBT is accessed through I2C of the master (= DAQ lpGBT).
        '''
        self.nodes = []
        self.rb = rb
        self.trigger = trigger
        if self.trigger:
            assert isinstance(master, LPGBT), "Trying to initialize a trigger lpGBT but got no lpGBT master."
            self.master = master
        self.LPGBT_CONST = LpgbtConstants()

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

        lpgbt.I2C_write(reg=0x118, val=6, master=2, slave_addr=0x70)
        sleep (0.1)
        lpgbt.I2C_write(reg=0x118, val=0, master=2, slave_addr=0x70)
        # eport rx inversions
        lpgbt.I2C_write(reg=0xe0, val=0x0a, master=2, slave_addr=0x70)
        lpgbt.I2C_write(reg=0xe2, val=0x0a, master=2, slave_addr=0x70)

        self.reset_trigger_mgts()

    def power_up_init(self):
        if not self.trigger:

            # toggle the uplink to and from 40MHz clock, for some reason this is
            # needed for the mgt to lock

            self.wr_adr(0x118, 6)
            sleep(0.1)
            self.wr_adr(0x118, 0)
        else:
            # servant lpgbt base configuration
            self.master.program_slave_from_file('configs/config_slave.txt')  #FIXME check if we still need this black box after power cycle.

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
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_GBTX_ADDR" % self.rb, 115)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_REGISTER_ADDR" % self.rb, adr)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_DATA_TO_GBTX" % self.rb, data)
        self.kcu.action("READOUT_BOARD_%d.SC.TX_WR" % self.rb)
        self.kcu.action("READOUT_BOARD_%d.SC.TX_START_WRITE" % self.rb)
        self.rd_flush()

    def rd_adr(self, adr):
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_GBTX_ADDR" % self.rb, 115)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_NUM_BYTES_TO_READ" % self.rb, 1)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_REGISTER_ADDR" % self.rb, adr)
        self.kcu.action("READOUT_BOARD_%d.SC.TX_START_READ" % self.rb)
        i = 0
        while (not self.kcu.read_node("READOUT_BOARD_%d.SC.RX_EMPTY" % self.rb)):
            self.kcu.action("READOUT_BOARD_%d.SC.RX_RD" % self.rb)
            read = self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_FROM_GBTX" % self.rb)
            if i == 6:
                return read
            i += 1
        print("lpgbt read failed!! SC RX empty")
        return 0xE9

    def wr_reg(self, id, data):
        node = self.get_node(id)
        if self.trigger:
            self.write_reg(self.master.I2C_write, self.master.I2C_read, node, data)  # inherited from RegParser
        else:
            self.write_reg(self.wr_adr, self.rd_adr, node, data)  # inherited from RegParser

    def rd_reg(self, id):
        node = self.get_node(id)
        data = self.read_reg(self.rd_adr, node)
        return data

    def rd_flush(self):
        i = 0
        while (not self.kcu.read_node("READOUT_BOARD_%d.SC.RX_EMPTY" % self.rb)):
            self.kcu.action("READOUT_BOARD_%d.SC.RX_RD" % self.rb)
            read = self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_FROM_GBTX" % self.rb)
            i = i + 1

    def configure_gpio_outputs(self, outputs=0x2401, defaults=0x0401):
        self.wr_adr(0x52, outputs >> 8)
        self.wr_adr(0x53, outputs & 0xFF)
        self.wr_adr(0x54, defaults >> 8)
        self.wr_adr(0x55, defaults & 0xFF)

    def set_uplink_alignment(self, val, link, quiet=False):
        if self.trigger:
            if not quiet:
                print ("Setting uplink alignment for trigger link %i to %i"%(link, val))
            id = "READOUT_BOARD_%d.LPGBT.TRIGGER.UPLINK.ALIGN_%d" % (self.rb, link)
        else:
            if not quiet:
                print ("Setting uplink alignment for DAQ link %i to %i"%(link, val))
            id = "READOUT_BOARD_%d.LPGBT.DAQ.UPLINK.ALIGN_%d" % (self.rb, link)
        self.kcu.write_node(id, val)

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
        #[0x0a7] EPTXDataRate
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX0DATARATE", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX1DATARATE", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX2DATARATE", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX3DATARATE", 0x3)

        #EPTXxxEnable
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX12ENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX10ENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX20ENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX00ENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX23ENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX02ENABLE", 0x1)

        #EPTXxxDriveStrength
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX6DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX4DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX8DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX0DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX11DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX_CHN_CONTROL.EPTX2DRIVESTRENGTH", 0x3)

        # enable mirror feature
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX0MIRRORENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX1MIRRORENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX2MIRRORENABLE", 0x1)
        self.wr_reg("LPGBT.RWF.EPORTTX.EPTX3MIRRORENABLE", 0x1)

        #turn on 320 MHz clocks
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK3FREQ",  0x4)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK5FREQ",  0x4)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK6FREQ",  0x4)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK7FREQ",  0x4)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK15FREQ", 0x4)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK16FREQ", 0x4)

        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK3DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK5DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK6DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK7DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK15DRIVESTRENGTH", 0x3)
        self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK16DRIVESTRENGTH", 0x3)

    def configure_eprx(self):
        print ("Configuring elink inputs...")
        # Enable Elink-inputs
    
        #set banks to 320 Mbps
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX0DATARATE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX1DATARATE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX2DATARATE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX3DATARATE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX4DATARATE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX5DATARATE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX6DATARATE", 1)
    
        #set banks to fixed phase
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX0TRACKMODE", 2)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX1TRACKMODE", 2)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX2TRACKMODE", 2)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX3TRACKMODE", 2)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX4TRACKMODE", 2)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX5TRACKMODE", 2)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX6TRACKMODE", 2)
    
        #enable inputs
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX00ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX01ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX02ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX03ENABLE", 1)
    
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX10ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX11ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX12ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX13ENABLE", 1)
    
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX20ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX21ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX22ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX23ENABLE", 1)
    
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX30ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX31ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX32ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX33ENABLE", 1)
    
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX40ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX41ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX42ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX43ENABLE", 1)
    
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX50ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX51ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX52ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX53ENABLE", 1)
    
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX60ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX61ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX62ENABLE", 1)
        self.wr_reg("LPGBT.RWF.EPORTRX.EPRX63ENABLE", 1)
    
        for i in [22]:
            self.wr_reg("LPGBT.RWF.EPORTRX.EPRX_CHN_CONTROL.EPRX%dINVERT" % i, 1)
    
        #enable 100 ohm termination
        for i in range (28):
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

    def read_adcs(self):
        self.init_adc()
        print("ADC Readings:")
        for i in range(16):
            name = ""
            conv = 0
            if (i==0 ): conv=1;      name="VTRX TH1"
            if (i==1 ): conv=1/0.55; name="1V4D * 0.55"
            if (i==2 ): conv=1/0.55; name="1V5A * 0.55"
            if (i==3 ): conv=1/0.33; name="2V5TX * 0.33"
            if (i==4 ): conv=1;      name="RSSI"
            if (i==5 ): conv=1;      name="N/A"
            if (i==6 ): conv=1/0.33; name="2V5RX * 0.33"
            if (i==7 ): conv=1;      name="RT1"
            if (i==8 ): conv=1;      name="EOM DAC (internal signal)"
            if (i==9 ): conv=1/0.42; name="VDDIO * 0.42 (internal signal)"
            if (i==10): conv=1/0.42; name="VDDTX * 0.42 (internal signal)"
            if (i==11): conv=1/0.42; name="VDDRX * 0.42 (internal signal)"
            if (i==12): conv=1/0.42; name="VDD * 0.42 (internal signal)"
            if (i==13): conv=1/0.42; name="VDDA * 0.42 (internal signal)"
            if (i==14): conv=1;      name="Temperature sensor (internal signal)"
            if (i==15): conv=1/0.50; name="VREF/2 (internal signal)"
    
            read = self.read_adc(i)
            print("\tch %X: 0x%03X = %f, reading = %f (%s)" % (i, read, read/1024., conv*read/1024., name))

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
            done = self.rd_reg("LPGBT.RO.ADC.ADCDONE")
    
        val = self.rd_reg("LPGBT.RO.ADC.ADCVALUEL")
        val |= self.rd_reg("LPGBT.RO.ADC.ADCVALUEH") << 8
    
        self.wr_reg("LPGBT.RW.ADC.ADCCONVERT", 0x0)
        self.wr_reg("LPGBT.RW.ADC.ADCENABLE", 0x1)
    
        return val

    def set_dac(self, v_out):
        if v_out >= 1.00:
            print ("Can't set the DAC to a value larger than 1.0 V!")
            return
        v_ref = 1.00
        value = int(v_out/v_ref*4096)
        lo_bits = value & 0xFF
        hi_bits = (value & ~lo_bits) >> 8
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
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEL", 0x0)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACVALUEH", 0x0)
        self.wr_reg("LPGBT.RWF.VOLTAGE_DAC.VOLDACENABLE", 0x0)

    def initialize(self):
        self.wr_adr(0x36, 0x80)  # "LPGBT.RWF.CHIPCONFIG.HIGHSPEEDDATAOUTINVERT"

        # turn on clock outputs
        print ("Configuring clocks now.")
        self.configure_clocks(0x0fffffff, 0x0)

        # setup up sca eptx/rx
        # sca_setup() # maybe not needed???

    def loopback(self, nloops=100):
        for i in range(nloops):
            wr = random.randint(0, 255)
            self.wr_adr(1, wr)
            rd = self.rd_adr(1)
            if wr != rd:
                print("ERR: %d wr=0x%08X rd=0x%08X" % (i, wr, rd))
                return
            if (i % (nloops/100) == 0 and i != 0):
                print("%i reads done..." % i)

    def set_gpio(self, ch, val, default=0x401):
        if (ch > 7):
            rd = default >> 8
            node = "LPGBT.RWF.PIO.PIOOUTH"
            ch = ch - 8
        else:
            node = "LPGBT.RWF.PIO.PIOOUTL"
            rd = default & 0xff

        if val == 0:
            rd = rd & (0xff ^ (1 << ch))
        else:
            rd = rd | (1 << ch)

        reg = self.get_node(node)
        adr = reg.address
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
    
        self.wr_reg("LPGBT.RW.TESTING.ULG0DATASOURCE", setting)
        self.wr_reg("LPGBT.RW.TESTING.ULG1DATASOURCE", setting)
        self.wr_reg("LPGBT.RW.TESTING.ULG2DATASOURCE", setting)
        self.wr_reg("LPGBT.RW.TESTING.ULG3DATASOURCE", setting)
        self.wr_reg("LPGBT.RW.TESTING.ULG4DATASOURCE", setting)
        self.wr_reg("LPGBT.RW.TESTING.ULG5DATASOURCE", setting)
        self.wr_reg("LPGBT.RW.TESTING.ULG6DATASOURCE", setting)
    
        if (setting == 4 or setting == 5):
            self.wr_reg("LPGBT.RW.TESTING.DPDATAPATTERN0", 0xff & (pattern >> 0))
            self.wr_reg("LPGBT.RW.TESTING.DPDATAPATTERN1", 0xff & (pattern >> 8))
            self.wr_reg("LPGBT.RW.TESTING.DPDATAPATTERN2", 0xff & (pattern >> 16))
            self.wr_reg("LPGBT.RW.TESTING.DPDATAPATTERN3", 0xff & (pattern >> 24))

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

    def I2C_write(self, reg=0x0, val=10, master=2, slave_addr=0x70):
        #Parameters specific to our FPGA##########
        #slave_addr: Which LPGBT chip we are referencing (depends on how the board is set up)
        #reg: register which is going to be written to. 0x0, 0x1, 0x2, 0x3 are all available for testing
        #the write process is specify the config parameters (a), load the data registers (b), then execute multi-write command word (c)
        #####################
        i2cm     = 2
        OFFSET_WR = i2cm*(self.LPGBT_CONST.I2CM1CMD - self.LPGBT_CONST.I2CM0CMD) #shift the master by 2 registers (we can change this)
        OFFSET_RD = i2cm*(self.LPGBT_CONST.I2CM1STATUS - self.LPGBT_CONST.I2CM0STATUS)
        regl = (int(reg) & 0xFF) >> 0
        regh = (int(reg)) >> 8
        address_and_data = [val]
        address_and_data.insert(0, regl)
        address_and_data.insert(1, regh)
        nbytes = len(address_and_data)
        #import pdb; pdb.set_trace()
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-cr-0x0
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA0+OFFSET_WR, nbytes<<self.LPGBT_CONST.I2CM_CR_NBYTES_of | 2<<self.LPGBT_CONST.I2CM_CR_FREQ_of)
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_CRA)# write config registers (a)
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-w-multi-4byte0-0x8
    
        for i, data_byte in enumerate(address_and_data): # there are 4 pages with 4 registers each
            page = i/4
            offset = i%4
            self.wr_adr(self.LPGBT_CONST.I2CM0DATA0 + OFFSET_WR + offset, int(data_byte))
            if i%4==3 or i==len(address_and_data)-1:
                # load the data we want to write into registers (b)
                self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, int(self.LPGBT_CONST.I2CM_W_MULTI_4BYTE0+page))
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-multi-0xc
        self.wr_adr(self.LPGBT_CONST.I2CM0ADDRESS+OFFSET_WR, slave_addr)# write the address of the follower
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_MULTI)# execute write (c)

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

    def I2C_read(self, reg=0x0, master=2, slave_addr=0x70, nbytes=1):
        #https://gitlab.cern.ch/lpgbt/pigbt/-/blob/master/backend/apiapp/lpgbtLib/lowLevelDrivers/MASTERI2C.py#L83
        i2cm      = master
	
        # we can also switch to sth like this:
        # i2cm1cmd = self.get_node('LPGBT.RW.I2C.I2CM1CMD').real_address

        OFFSET_WR = i2cm*(self.LPGBT_CONST.I2CM1CMD - self.LPGBT_CONST.I2CM0CMD) #using the offset trick to switch between masters easily
        OFFSET_RD = i2cm*(self.LPGBT_CONST.I2CM1STATUS - self.LPGBT_CONST.I2CM0STATUS)
    
        regl = (int(reg) & 0xFF) >> 0
        regh = (int(reg)) >> 8
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-cr-0x0
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA0+OFFSET_WR, 2<<self.LPGBT_CONST.I2CM_CR_NBYTES_of | (2<<self.LPGBT_CONST.I2CM_CR_FREQ_of))
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_CRA) #write to config register
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-w-multi-4byte0-0x8
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA0 + OFFSET_WR , regl)
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA1 + OFFSET_WR , regh)
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_W_MULTI_4BYTE0) # prepare a multi-write
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-multi-0xc
        self.wr_adr(self.LPGBT_CONST.I2CM0ADDRESS+OFFSET_WR, slave_addr)
        self.wr_adr(self.LPGBT_CONST.I2CM0CMD+OFFSET_WR, self.LPGBT_CONST.I2CM_WRITE_MULTI)# execute multi-write
    
        # https://lpgbt.web.cern.ch/lpgbt/v0/i2cMasters.html#i2c-write-cr-0x0
        self.wr_adr(self.LPGBT_CONST.I2CM0DATA0+OFFSET_WR, nbytes<<self.LPGBT_CONST.I2CM_CR_NBYTES_of | 2<<self.LPGBT_CONST.I2CM_CR_FREQ_of)
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
                self.I2C_write(reg=adr, val=wr, master=master, slave_addr=slave_addr)
                rd = self.I2C_read(reg=adr, master=master, slave_addr=slave_addr)
                if (wr!=rd):
                    print("LPGBT readback error 0x%02X != 0x%02X at adr %d" % (wr, rd, adr))

    def read_temp_i2c(self):
        res = self.I2C_read(reg=0x0, master=1, slave_addr=0x48, nbytes=2)
        temp_dig = (res[0] << 4) + (res[1] >> 4)
        return temp_dig*0.0625


if __name__ == '__main__':

    lpgbt = LPGBT()
    lpgbt.parse_xml('../address_table/lpgbt.xml', top_node_name="LPGBT")
    lpgbt.dump(nMax=10)
