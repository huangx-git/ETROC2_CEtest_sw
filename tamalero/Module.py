#!/usr/bin/env python3
import os
from tamalero.utils import load_yaml
from tamalero.colors import red, green
from tamalero.ETROC import ETROC
from tamalero.Monitoring import Lock
from time import sleep

class Module:
    def __init__(self, rb, i=1):
        # don't like that this also needs a RB
        # think about a better solution
        map_file = os.path.expandvars(f'$TAMALERO_BASE/configs/module_mapping_v{rb.ver}.yaml')
        self.config = load_yaml(map_file)[f'm{i}']
        #self.regs = load_yaml(os.path.expandvars('$TAMALERO_BASE/address_table/ETROC2.yaml'))
        #self.regs_em = ['disScrambler', 'singlePort', 'mergeTriggerData', 'triggerGranularity']
        self.i = i
        self.rb = rb

        self.ETROCs = []
        for j in range(len(self.config['elinks'])):
            if self.config['i2c']['master']=='fake':
                self.ETROCs.append(
                    ETROC(
                        usefake=True,
                        master=self.config['i2c']['master'],
                        i2c_channel=self.config['i2c']['channel'],
                        elink=self.config['elinks'][j],
                        i2c_adr = self.config['addresses'][j],
                    ))
            else:
                self.ETROCs.append(
                    ETROC(
                        rb=rb,
                        master=self.config['i2c']['master'],
                        i2c_channel=self.config['i2c']['channel'],
                        elink=self.config['elinks'][j],
                        i2c_adr = self.config['addresses'][j],
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

    def show_status(self):
        len_corrector = len(''.join([str(x) for x in self.config['elinks']]))

        print ('┏━┳━' + 25*'━' + '━┳━┓')
        print ('┃○┃ ' + 25*' ' + ' ┃○┃')
        print ('┃ ┃ ' + '{:10}{:<15}'.format("Module:", self.i) + ' ┃ ┃' )
        ver = self.ETROCs[0].ver
        print ('┃ ┃ ' + '{:16}{:9}'.format("Emulator FW ver.",ver) + ' ┃ ┃' )
        #print ('┃ ┃ ' + 25*' ' + ' ┃ ┃')
        col = green if self.ETROCs[0].connected else red
        prefix = '' if self.ETROCs[0].connected else "Not "
        print ('┃ ┃ ' + col('{:25}'.format(prefix+"Connected:")) + ' ┃ ┃' )
        print ('┃ ┃ ' + col(' {:12}{:12}'.format('i2c master:', self.ETROCs[0].master)) + ' ┃ ┃')
        print ('┃ ┃ ' + col(' {:12}{:<12}'.format('channel:', self.ETROCs[0].i2c_channel )) + ' ┃ ┃')

        print ('┃ ┃ ' + '{:25}'.format("DAQ links:") + ' ┃ ┃' )
        stats = [ green(str(etroc.elink)) if etroc.daq_locked else red(str(etroc.elink)) for etroc in self.ETROCs ]
        print ('┃ ┃ ' + ' {} {} {} {}'.format(*stats) + (25-len_corrector - 4)*' ' + ' ┃ ┃' )

        print ('┃ ┃ ' + '{:25}'.format("Trigger links:") + ' ┃ ┃' )
        stats = [ green(str(etroc.elink)) if etroc.trig_locked else red(str(etroc.elink)) for etroc in self.ETROCs ]
        print ('┃ ┃ ' + ' {} {} {} {}'.format(*stats) + (25-len_corrector - 4)*' ' + ' ┃ ┃' )


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

            # "global" lock
            #self.rb.SCA.lock()
            self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], to=0)
            sleep(0.25)
            for i in range(status):
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], to=1)
                sleep(0.25)
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], to=0)
                sleep(0.25)

            if status > 0:
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], to=1)
            else:
                self.rb.SCA.set_gpio(self.rb.SCA.gpio_mapping[self.config['status']]['pin'], to=0)
        #self.rb.SCA.unlock()

            #sleep(5)
