'''
Documentation: https://edms.cern.ch/ui/file/1719330/1/VLplus_quadLDD_spec_v1.2_prototypes.pdf
'''

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

    def __init__(self, master):
        '''
        master: the lpGBT master to the VTRX
        '''
        self.master = master

    def rd_adr(self, adr):
        return self.master.I2C_read(adr, master=2, slave_addr=0x50, adr_nbytes=1)

    def wr_adr(self, adr, data):
        self.master.I2C_write(adr, val=data, master=2, slave_addr=0x50, adr_nbytes=1)

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
            line = [channel_status_bits[b]] + [ ((ctrl_reg[i] & 2**b)>0) for i in range(4) ]
            print("{:40}{:^12}{:^12}{:^12}{:^12}".format(*line))

    def enable(self, channel=0):
        ctrl_reg = self.rd_adr(0x04 + 4*(channel))
        self.wr_adr(0x04 + 4*(channel), ctrl_reg | 1)

    def disable(self, channel=0):
        ctrl_reg = self.rd_adr(0x04 + 4*(channel))
        self.wr_adr(0x04 + 4*(channel), ctrl_reg >> 1 << 1)
