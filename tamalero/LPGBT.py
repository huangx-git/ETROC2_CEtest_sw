from module_test_sw.RegParser import RegParser


class LPGBT(RegParser):

    def __init__(self, rb=0, trigger=False):
        self.nodes = []
        self.rb = rb
        self.trigger = trigger


    def connect_KCU(self, kcu):
        '''
        We need to connect to the KCU somehow
        '''
        self.kcu = kcu


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
            #print("i=%d, data=0x%02x" % (i,read))
            if i == 6:
                return read
            i += 1
        print("lpgbt read failed!! SC RX empty")
        return 0xE9


    def wr_reg(self, id, data):
        node = self.get_node(id)
        self.write_reg(self.wr_adr, self.rd_adr, node, data)


    def rd_flush(self):
        i = 0
        while (not self.kcu.read_node("READOUT_BOARD_%d.SC.RX_EMPTY" % self.rb)):
            self.kcu.action("READOUT_BOARD_%d.SC.RX_RD" % self.rb)
            read = self.kcu.read_node("READOUT_BOARD_%d.SC.RX_DATA_FROM_GBTX" % self.rb)
            i= i + 1


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
        print ("Configuring eport dlls...")
        #2.2.2. Uplink: ePort Inputs DLL's
        #[0x034] EPRXDllConfig
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLCURRENT", 0x1)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLCONFIRMCOUNT", 0x1)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLFSMCLKALWAYSON", 0x0)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDLLCOARSELOCKDETECTION", 0x0)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXENABLEREINIT", 0x0)
        self.wr_reg("LPGBT.RWF.CLOCKGENERATOR.EPRXDATAGATINGENABLE", 0x1)


    def initialize(self):
        self.wr_adr(0x36, 0x80)  # "LPGBT.RWF.CHIPCONFIG.HIGHSPEEDDATAOUTINVERT"

        # turn on clock outputs
        self.configure_clocks(0x0fc0081f, 0x0)

        ## setup up sca eptx/rx
        #sca_setup() # maybe not needed???


    def status(self):
        print("Readout Board %s LPGBT Link Status:"%self.rb)
        print("{:<8}{:<8}{:<50}{:<8}".format("Address", "Perm.", "Name", "Value"))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.READY"%self.rb))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.READY"%self.rb))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.FEC_ERR_CNT"%self.rb))


if __name__ == '__main__':

    lpgbt = LPGBT()
    lpgbt.parse_xml('../address_table/lpgbt.xml')
    lpgbt.dump(nMax=10)
