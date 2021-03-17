from tamalero.RegParser import RegParser

import random


class LPGBT(RegParser):

    def __init__(self, rb=0, trigger=False, flavor='small'):
        self.nodes = []
        self.rb = rb
        self.trigger = trigger

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

    def set_daq_uplink_alignment(self, val, link):
        id = "READOUT_BOARD_%d.LPGBT.DAQ.UPLINK.ALIGN_%d" % (self.rb, link)
        self.kcu.write_node(id, val)

    def configure_clocks(self, en_mask, invert_mask=0):
        for i in range(27):
            if 0x1 & (en_mask >> i):
                self.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK%dFREQ" % i, 1)
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
        self.configure_clocks(0x0fc0081f, 0x0)

        # setup up sca eptx/rx
        # sca_setup() # maybe not needed???

    def status(self):
        print("Readout Board %s LPGBT Link Status:" % self.rb)
        print("{:<8}{:<8}{:<50}{:<8}".format("Address", "Perm.", "Name", "Value"))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.READY" % self.rb))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.READY" % self.rb))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.FEC_ERR_CNT" % self.rb))

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


if __name__ == '__main__':

    lpgbt = LPGBT()
    lpgbt.parse_xml('../address_table/lpgbt.xml', top_node_name="LPGBT")
    lpgbt.dump(nMax=10)
