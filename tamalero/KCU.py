"""
Control board class (KCU105). Depends on uhal.
"""
import uhal


class KCU:

    def __init__(self,
                 name="my_device",
                 ipb_path="ipbusudp-2.0://192.168.0.10:50001",
                 adr_table="../module_test_fw/address_tables/etl_test_fw.xml",
                 dummy=False):

        uhal.disableLogging()

        if not dummy:
            try:
                self.hw = uhal.getDevice("my_device", ipb_path, "file://" + adr_table)
            except:
                raise Exception("uhal can't get device at"+adr_table)
        else:
            self.hw = None
        self.readout_boards = []
        self.auto_dispatch = True  # default -> True

    def toggle_dispatch(self):
        self.auto_dispatch = False

    def dispatch(self):
        self.hw.dispatch()
        self.auto_dispatch = True

    def write_node(self, id, value):
        reg = self.hw.getNode(id)
        if (reg.getPermission() == uhal.NodePermission.WRITE):
            self.action_reg(reg)
        else:
            reg.write(value)
            if self.auto_dispatch:
                self.dispatch()

    def read_node(self, id):
        reg = self.hw.getNode(id)
        ret = reg.read()
        if self.auto_dispatch:
            self.dispatch()
        return ret

    def action_reg(self, reg):
        addr = reg.getAddress()
        mask = reg.getMask()
        self.hw.getClient().write(addr, mask)
        if self.auto_dispatch:
            self.dispatch()

    def action(self, id):
        reg = self.hw.getNode(id)
        self.action_reg(reg)

    def firmware_version(self, quiet=False, string=True):

        nodes = ("FW_INFO.HOG_INFO.GLOBAL_DATE",
                 "FW_INFO.HOG_INFO.GLOBAL_TIME",
                 "FW_INFO.HOG_INFO.GLOBAL_VER",
                 "FW_INFO.HOG_INFO.GLOBAL_SHA",)

        if not quiet:
            for node in nodes:
                self.print_reg(self.hw.getNode(node))

        res = self.read_node("FW_INFO.HOG_INFO.GLOBAL_VER")
        if string:
            return "%s.%s.%s"%(res >> 24, (res >> 16) & 0xFF, res & 0xFFFF)
        else:
            return {"major": res >> 24, "minor": (res >> 16) & 0xFF, "patch": res & 0xFFFF}

    def firmware_sha(self):
        res = self.read_node("FW_INFO.HOG_INFO.GLOBAL_SHA")
        return hex(res).strip('0x0')

    def xml_sha(self):
        res = self.read_node("FW_INFO.HOG_INFO.XML_SHA")
        return hex(res).strip('0x0')

    def get_serial(self):
        # placeholder
        return "000000"

    def status(self):
        print("LPGBT Link Status from KCU:")
        for id in self.hw.getNodes(".*LPGBT.*DAQ.*DOWNLINK.*READY"):
            self.print_reg(self.hw.getNode(id), use_color=True, threshold=1)
        for id in self.hw.getNodes(".*LPGBT.*DAQ.*UPLINK.*READY"):
            self.print_reg(self.hw.getNode(id), use_color=True, threshold=1)
        for id in self.hw.getNodes(".*LPGBT.*DAQ.*UPLINK.*FEC_ERR_CNT"):
            self.print_reg(self.hw.getNode(id), use_color=True, threshold=1, invert=True)
        for id in self.hw.getNodes(".*LPGBT.*TRIGGER.*UPLINK.*READY"):
            self.print_reg(self.hw.getNode(id), use_color=True, threshold=1)
        for id in self.hw.getNodes(".*LPGBT.*TRIGGER.*UPLINK.*FEC_ERR_CNT"):
            self.print_reg(self.hw.getNode(id), use_color=True, threshold=1, invert=True)

        self.check_clock_frequencies()


    def print_reg(self, reg, threshold=1, maxval=0xFFFFFFFF, use_color=False, invert=False):
        from tamalero.colors import green, red, dummy
        val = reg.read()
        id = reg.getPath()
        self.dispatch()
        if use_color:
            if invert:
                colored = green if (val < threshold and val < maxval) else red
            else:
                colored = green if (val >= threshold and val < maxval) else red
        else:
            colored = dummy
        print(colored(self.format_reg(reg.getAddress(), id[4:], val,
                              self.format_permission(reg.getPermission()))))

    def format_reg(self, address, name, val, permission=""):
        s = "{:<8}{:<8}{:<50}".format("0x%04X" % address, permission, name)
        if (val != -1):
            s = s + "{:<8}".format("0x%08X" % val)
        return s

    def format_permission(self, perm):
        if perm == uhal.NodePermission.READ:
            return "r"
        if perm == uhal.NodePermission.READWRITE:
            return "rw"
        if perm == uhal.NodePermission.WRITE:
            return "w"

    def connect_readout_board(self, rb, dummy=False):
        self.readout_boards.append(rb)

        if not dummy:
            rb.connect_KCU(self)  # not sure if this is actually useful
        return rb

    def check_clock_frequencies(self):
        clocks = (('FW_INFO.CLK125_FREQ', 125000000),
                  ('FW_INFO.CLK320_FREQ', 320640000),
                  ('FW_INFO.CLK_40_FREQ',  40080000),
                  ('FW_INFO.IPBCLK_FREQ',  40080000),
                  ('FW_INFO.REFCLK_FREQ', 320640000),
                  ('FW_INFO.RXCLK0_FREQ', 320640000),
                  ('FW_INFO.RXCLK1_FREQ', 320640000),
                  ('FW_INFO.TXCLK0_FREQ', 320640000),
                  ('FW_INFO.TXCLK1_FREQ', 320640000))

        # freq = int(rd) / 1000000.0
        # print("%s = %6.2f MHz" % (id, freq))

        for clock in clocks:
            self.print_reg(self.hw.getNode(clock[0]), use_color=True, threshold=clock[1] - 2000, maxval=clock[1] + 2000)
