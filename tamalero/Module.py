#!/usr/bin/env python3
import os
from tamalero.utils import load_yaml
from tamalero.colors import red, green

class Module:
    def __init__(self, rb, i=1):
        # don't like that this also needs a RB
        # think about a better solution
        self.config = load_yaml(os.path.expandvars('$TAMALERO_BASE/configs/module_mapping.yaml'))[f'm{i}']
        self.regs = load_yaml(os.path.expandvars('$TAMALERO_BASE/address_table/ETROC_HW_emulator.yaml'))
        self.i = i
        #self.config = read_mapping()

        self.I2C_master = rb.DAQ_LPGBT if self.config['i2c']['master'] == 'lpgbt' else rb.SCA
        self.rb = rb
        # check if connected
        self.connected = self.I2C_read(reg=0x13) or self.I2C_read(reg=0x13) is 0

    def configure(self):
        if self.connected:
            self.wr_reg('singlePort', 0)
            self.wr_reg('mergeTrigData', 0)
            self.wr_reg('disSCR', 1)

    def I2C_write(self, reg=0x0, val=0x0):
        self.I2C_master.I2C_write(
            reg=reg,
            val=val,
            master=self.config['i2c']['channel'],
            slave_addr=0x72  # NOTE this will need to change in the future
        )

    def I2C_read(self, reg=0x0):
        return self.I2C_master.I2C_read(
            reg=reg,
            master=self.config['i2c']['channel'],
            slave_addr=0x72  # NOTE this will need to change in the future
        )

    def wr_reg(self, reg, val):
        adr   = self.regs[reg]['adr']
        shift = self.regs[reg]['shift']
        mask  = self.regs[reg]['mask']

        orig_val = self.I2C_read(adr)
        new_val = ((val<<shift)&mask) | (orig_val&(~mask))

        self.I2C_write(adr, new_val)

    def rd_reg(self, reg):
        adr = self.regs[reg]['adr']
        mask = self.regs[reg]['mask']
        shift = self.regs[reg]['shift']

        return (self.I2C_read(adr)&mask) >> shift

    def get_elink_status(self):
        locked = self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.ETROC_LOCKED").value()
        locked_slave = self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.ETROC_LOCKED_SLAVE").value()

        self.daq_elinks = {}
        self.trig_elinks = {}
        for elink in self.config['elinks']:
            if (locked >> elink) & 1:
                self.daq_elinks[elink] = True
            else:
                self.daq_elinks[elink] = False
            if (locked_slave >> elink) & 1:
                self.trig_elinks[elink] = True
            else:
                self.trig_elinks[elink] = False


    def show_status(self):
        self.get_elink_status()
        len_corrector = len(''.join([str(x) for x in self.trig_elinks.keys()]))

        print ('|-|-' + 25*'-' + '-|-|')
        print ('|O| ' + 25*' ' + ' |O|')
        print ('| | ' + '{:10}{:<15}'.format("Module:", self.i) + ' | |' )
        #print ('| | ' + 25*' ' + ' | |')
        col = green if self.connected else red
        prefix = '' if self.connected else "Not "
        print ('| | ' + col('{:25}'.format(prefix+"Connected:")) + ' | |' )
        print ('| | ' + col(' {:12}{:12}'.format('i2c master:', self.config['i2c']['master'])) + ' | |')
        print ('| | ' + col(' {:12}{:<12}'.format('channel:', self.config['i2c']['channel'] )) + ' | |')

        print ('| | ' + '{:25}'.format("DAQ links:") + ' | |' )
        stats = [ green(str(l)) if (self.daq_elinks[l]==True) else red(str(l)) for l in self.daq_elinks.keys() ]
        print ('| | ' + ' {} {} {} {}'.format(*stats) + (25-len_corrector - 4)*' ' + ' | |' )

        print ('| | ' + '{:25}'.format("Trigger links:") + ' | |' )
        stats = [ green(str(l)) if (self.trig_elinks[l]==True) else red(str(l)) for l in self.trig_elinks.keys() ]
        print ('| | ' + ' {} {} {} {}'.format(*stats) + (25-len_corrector - 4)*' ' + ' | |' )
        #print ('| | ' + 25*' ' + ' | |')


        print ('|O| ' + 25*' ' + ' |O|')
        print ('|-|-' + 25*'-' + '-|-|')


    def show_emulator_status(self):
        print("+" + 31*"-" + "+")
        print("|{:^31s}|".format("ETROC Hardware Emulator"))
        print("|" + 31*" " + "|")

        for reg in self.regs:
            col = green if self.rd_reg(reg) else red
            print("| " + col('{:25}{:4}'.format(reg, hex(self.rd_reg(reg)))) + " |")

        print("+" + 31*"-" + "+")
