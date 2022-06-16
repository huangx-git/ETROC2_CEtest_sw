'''
Documentation: https://edms.cern.ch/ui/file/1719330/1/VLplus_quadLDD_spec_v1.2_prototypes.pdf
'''

from tamalero.colors import conditional

global_status_bits = {
    0: "Global Chip Enable",
    1: "Global Limiting Amplifier Enable",
    2: "Global Bias Circuit Enable",
    3: "Global Modulation Circuit Enable",
    4: "Global Pre-emphasis Enable",
}

channel_status_bits = {
    0: "Channel Enable",
    1: "Limiting Amplifier Enable",
    2: "Biasing Circuit Enable",
    3: "Modulation Circuit Enable",
    4: "Rising Edge Pre-emphasis",
    5: "Falling Edge Pre-emphasis",
}


class VTRX:

    def __init__(self, master, disable_channels=[]):
        '''
        master: the lpGBT master to the VTRX
        '''
        self.master = master

        for ch in disable_channels:
            print (f"Disabling VTRx+ channel {ch}")
            self.disable(channel=ch)


    def reset(self, hard=False, toggle_channels=[]):
        if hard:
            # enable / disable
            self.master.set_gpio(13,1)
            self.master.set_gpio(13,0)
        # reset_b
        self.master.set_gpio(10,0)
        self.master.set_gpio(10,1)

        for ch in toggle_channels:
            self.disable(channel=ch)
            self.enable(channel=ch)

    def rd_adr(self, adr):
        return self.master.I2C_read(adr, master=2, slave_addr=0x50, adr_nbytes=1)

    def wr_adr(self, adr, data, ignore_response=False):
        self.master.I2C_write(adr, val=data, master=2, slave_addr=0x50, adr_nbytes=1, ignore_response=ignore_response)

    def status(self, quiet=False):
        global_status = self.rd_adr(0x0)

        print("\n## VTRx+ status:")
        for b in global_status_bits.keys():
            print("{:40}{:>2}".format(global_status_bits[b], (global_status & 2**b)>0))

        self.channel_status()

        return global_status

    def channel_status(self):
        ctrl_reg = {i: self.rd_adr(0x04 + 4*(i)) for i in range(4) }
        print("\n## VTRx+ Channel status:")
        header = [""] + ["Channel %s"%i for i in range(4) ]
        print("{:40}{:12}{:12}{:12}{:12}".format(*header))
        for b in channel_status_bits.keys():
            #line = [channel_status_bits[b]] + [ conditional((ctrl_reg[i] & 2**b)>0) for i in range(4) ]
            line = [channel_status_bits[b]] + [ ((ctrl_reg[i] & 2**b)>0) for i in range(4) ]
            print("{:40}{:^12}{:^12}{:^12}{:^12}".format(*line))

    def enable(self, channel=0):
        if channel == 0:
            ctrl_reg = 15  # we can't read back if channel 0 is disabled, just set to default values
        else:
            ctrl_reg = self.rd_adr(0x04 + 4*(channel))
        self.wr_adr(0x04 + 4*(channel), ctrl_reg | 1)

    def disable(self, channel=0):
        ignore_response = True if channel == 0 else False
        ctrl_reg = self.rd_adr(0x04 + 4*(channel))
        self.wr_adr(0x04 + 4*(channel), ctrl_reg >> 1 << 1, ignore_response=ignore_response)

    def preemph_enable(self):
        adr = 0x0
        ctrl_reg = self.rd_adr(0x0)
        self.wr_adr(adr, (ctrl_reg) | (1<<4))

    def preemph_disable(self):
        adr = 0x0
        ctrl_reg = self.rd_adr(0x0)
        self.wr_adr(adr, (ctrl_reg) & (0xff ^ (1<<4)))

    def set_preemph_rising(self, channel=0, enable=True):
        ctrl_reg = self.rd_adr(0x04 + 4*(channel))
        if (enable):
            self.wr_adr(0x04 + 4*(channel), (ctrl_reg) | (1 << 4))
        else:
            self.wr_adr(0x04 + 4*(channel), (ctrl_reg) & (0xff ^ (1 << 4)))

    def set_preemph_falling(self, channel=0, enable=True):
        ctrl_reg = self.rd_adr(0x04 + 4*(channel))
        if (enable):
            self.wr_adr(0x04 + 4*(channel), (ctrl_reg) | (1 << 5))
        else:
            self.wr_adr(0x04 + 4*(channel), (ctrl_reg) & (0xff ^ (1 << 5)))

    def set_bias_current(self, channel=0, current=0x2f):
        ctrl_reg = self.rd_adr(0x5 + 4*(channel))
        self.wr_adr(0x5 + 4*(channel), 0x7f & current)

    def set_modulation_current(self, channel=0, current=0x26):
        ctrl_reg = self.rd_adr(0x6 + 4*(channel))
        self.wr_adr(0x6 + 4*(channel), 0x7f & current)

    def get_modulation_current(self, channel=0):
        ctrl_reg = self.rd_adr(0x6 + 4*(channel))
        return ctrl_reg

    def set_emphasis_amplitude(self, channel=0, amplitude=0x0):
        ctrl_reg = self.rd_adr(0x07 + 4*(channel))
        self.wr_adr(0x7 + 4*(channel), amplitude & 0x7)
