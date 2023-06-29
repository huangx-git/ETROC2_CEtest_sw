#!/usr/bin/env python3
import os
from tamalero.utils import load_yaml
from tamalero.colors import red, green
from tamalero.ETROC import ETROC
from tamalero.Monitoring import Lock
from time import sleep

class Module:
    def __init__(self, rb, i=1, strict=False):
        # don't like that this also needs a RB
        # think about a better solution
        self.config = rb.configuration['modules'][i]
        self.breed = rb.config
        #self.config = load_yaml(map_file)[f'm{i}']
        #self.regs = load_yaml(os.path.expandvars('$TAMALERO_BASE/address_table/ETROC2.yaml'))
        #self.regs_em = ['disScrambler', 'singlePort', 'mergeTriggerData', 'triggerGranularity']
        self.i = i
        self.rb = rb

        self.ETROCs = []
        for j in range(len(self.config['addresses'])):
            if self.config['i2c']['master']=='fake':
                self.ETROCs.append(
                    ETROC(
                        #usefake=,
                        master=self.config['i2c']['master'],
                        i2c_channel=self.config['i2c']['channel'],
                        elinks={k: self.config['elinks'][j][k] for k in range(len(self.config['elinks'][j]))},
                        i2c_adr = self.config['addresses'][j],
                        reset = None,
                        breed = 'software'
                    ))
            else:
                self.ETROCs.append(
                    ETROC(
                        rb          = rb,
                        master      = self.config['i2c']['master'],
                        i2c_channel = self.config['i2c']['channel'],
                        elinks={k: self.config['elinks'][j][k] for k in range(len(self.config['elinks'][j]))},
                        #elinks      = self.config['elinks'][j],
                        i2c_adr     = self.config['addresses'][j],
                        strict      = strict,
                        reset = self.config['reset'],
                        breed = self.breed,
                    ))

    #def configure(self):
    #    if self.connected:
    #        self.wr_reg('singlePort', 0)
    #        self.wr_reg('mergeTriggerData', 0)
    #        self.wr_reg('disScrambler', 1)

    #def I2C_write(self, reg=0x0, val=0x0):
    #    self.I2C_master.I2C_write(
    #        reg=reg,
    #        val=val,
    #        master=self.config['i2c']['channel'],
    #        slave_addr=0x72,  # NOTE this will need to change in the future
    #    )

    #def I2C_read(self, reg=0x0):
    #    return self.I2C_master.I2C_read(
    #        reg=reg,
    #        master=self.config['i2c']['channel'],
    #        slave_addr=0x72,  # NOTE this will need to change in the future
    #    )

    #def wr_reg(self, reg, val):
    #    adr   = self.regs[reg]['regadr']
    #    shift = self.regs[reg]['shift']
    #    mask  = self.regs[reg]['mask']

    #    orig_val = self.I2C_read(adr)
    #    new_val = ((val<<shift)&mask) | (orig_val&(~mask))

    #    self.I2C_write(adr, new_val)

    #def rd_reg(self, reg):
    #    adr = self.regs[reg]['regadr']
    #    mask = self.regs[reg]['mask']
    #    shift = self.regs[reg]['shift']

    #    return (self.I2C_read(adr)&mask) >> shift

    def get_locked_links(self):
        self.locked = {0:[], 1:[]}
        self.unlocked = {0:[], 1:[]}
        for etroc in self.ETROCs:
            etroc.get_elink_status()
            for i in [0,1]:
                if i in etroc.links_locked:
                    for j, link in enumerate(etroc.elinks[i]):
                        if etroc.links_locked[i][j]:
                            self.locked[i].append(link)
                        else:
                            self.unlocked[i].append(link)
        return {'locked': self.locked, 'unlocked': self.unlocked}

    
    def show_status(self):
        self.get_locked_links()
        len_corrector_0 = len(' '.join([str(x) for x in self.locked[0] + self.unlocked[0]]))
        len_corrector_1 = len(' '.join([str(x) for x in self.locked[1] + self.unlocked[1]]))
        if len_corrector_0 == 0: len_corrector_0 = -1
        if len_corrector_1 == 0: len_corrector_1 = -1

        print ('┏━┳━' + 25*'━' + '━┳━┓')
        print ('┃○┃ ' + 25*' ' + ' ┃○┃')
        print ('┃ ┃ ' + '{:10}{:<15}'.format("Module:", self.i) + ' ┃ ┃' )
        ver = self.ETROCs[0].get_ver()
        print ('┃ ┃ ' + '{:16}{:9}'.format("Firmware ver.",ver) + ' ┃ ┃' )
        #print ('┃ ┃ ' + 25*' ' + ' ┃ ┃')
        col = green if self.ETROCs[0].connected else red
        prefix = '' if self.ETROCs[0].connected else "Not "
        print ('┃ ┃ ' + col('{:25}'.format(prefix+"Connected:")) + ' ┃ ┃' )
        print ('┃ ┃ ' + col(' {:12}{:12}'.format('i2c master:', self.ETROCs[0].master)) + ' ┃ ┃')
        print ('┃ ┃ ' + col(' {:12}{:<12}'.format('channel:', self.ETROCs[0].i2c_channel )) + ' ┃ ┃')

        print ('┃ ┃ ' + '{:25}'.format("lpGBT 1 links:") + ' ┃ ┃' )
        stats = [ green(str(l)) for l in self.locked[0] ] + [red(str(l)) for l in self.unlocked[0]]
        print ('┃ ┃ ' + (' {}'*len(self.locked[0]+self.unlocked[0])).format(*stats) + (24-len_corrector_0)*' ' + ' ┃ ┃' )

        print ('┃ ┃ ' + '{:25}'.format("lpGBT 2 links:") + ' ┃ ┃' )
        stats = [ green(str(l)) for l in self.locked[1] ] + [red(str(l)) for l in self.unlocked[1]]
        print ('┃ ┃ ' + (' {}'*len(self.locked[1]+self.unlocked[1])).format(*stats) + (24-len_corrector_1)*' ' + ' ┃ ┃' )


        print ('┃○┃ ' + 25*' ' + ' ┃○┃')
        print ('┗━┻━' + 25*'━' + '━┻━┛')

    def monitor(self):
        with Lock(self.rb.SCA) as l:
            status = 0
            if self.ETROCs[0].is_connected(): status += 1
            for etroc in self.ETROCs:
                etroc.get_elink_status()
                if etroc.daq_locked:
                    status += 1

            self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], 0)
            sleep(0.25)
            for i in range(status):
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], 1)
                sleep(0.25)
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], 0)
                sleep(0.25)

            if status > 0:
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], 1)
            else:
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], 0)
