import os
from tamalero.LPGBT import LPGBT
from tamalero.SCA import SCA
from tamalero.utils import get_temp
from tamalero.VTRX import VTRX

from time import sleep

class ReadoutBoard:

    def __init__(self, rb=0, trigger=True, flavor='small'):
        '''
        create a readout board.
        trigger: if true, also configure a trigger lpGBT
        '''
        self.rb = rb
        self.flavor = flavor

        self.trigger = trigger

        self.DAQ_LPGBT = LPGBT(rb=rb, flavor=flavor)
        self.DAQ_LPGBT.parse_xml(os.path.expandvars('$TAMALERO_BASE/address_table/lpgbt.xml'))

        self.VTRX = VTRX(self.DAQ_LPGBT)

        self.SCA = SCA(rb=rb, flavor=flavor)

    def get_trigger(self):
        # Self-check if a trigger lpGBT is present, if trigger is not explicitely set to False
        sleep(0.5)
        test_read = self.DAQ_LPGBT.I2C_read(reg=0x0, master=2, slave_addr=0x70, quiet=True)
        if test_read is not None and self.trigger:
            print ("Found trigger lpGBT, will configure it now.")
            self.trigger = True
        elif test_read is None:
            print ("No trigger lpGBT found.")
            self.trigger = False
        else:
            print ("Trigger lpGBT was found, but will not be added.")

        if self.trigger:
            self.TRIG_LPGBT = LPGBT(rb=self.rb, flavor=self.flavor, trigger=True, master=self.DAQ_LPGBT)
            self.TRIG_LPGBT.parse_xml(os.path.expandvars('$TAMALERO_BASE/address_table/lpgbt.xml'))
            self.TRIG_LPGBT.connect_KCU(self.kcu)
            print ("Connected to trigger lpGBT to KCU.")


    def connect_KCU(self, kcu):
        self.kcu = kcu
        self.DAQ_LPGBT.connect_KCU(kcu)
        self.SCA.connect_KCU(kcu)

    def sca_setup(self):
        # should this live here? I suppose so...
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRXECTERM", 1)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRXECENABLE", 1)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRXECACBIAS", 0)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRXECINVERT", 1)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRXECPHASESELECT", 8)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRXECTRACKMODE", 2)

        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTTX.EPTXECINVERT", 1)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTTX.EPTXECENABLE", 1)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTTX.EPTXECDRIVESTRENGTH", 4)

        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK28FREQ", 1)  # 1 =  40mhz
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK28INVERT", 1)
        self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTCLK.EPCLK28DRIVESTRENGTH", 4)

    def sca_hard_reset(self):
        # should this live here? I suppose so...
        bit = 0
        self.DAQ_LPGBT.set_gpio(bit, 0)
        self.DAQ_LPGBT.set_gpio(bit, 1)

    def find_uplink_alignment(self, scan_time=1, default=0):
        print ("Scanning for uplink alignment")
        alignment = {}
        # make alignment dict
        for link in ['Link 0', 'Link 1']:
            alignment[link] = {i:default for i in range(24)}
        # now, scan
        for shift in range(8):
            for channel in range(24):
                self.DAQ_LPGBT.set_uplink_alignment(shift, channel, quiet=True)
                if self.trigger:
                    self.TRIG_LPGBT.set_uplink_alignment(shift, channel, quiet=True)
            self.DAQ_LPGBT.set_uplink_group_data_source("normal")  # actually needed??
            self.DAQ_LPGBT.set_downlink_data_src('upcnt')
            self.DAQ_LPGBT.reset_pattern_checkers()
            sleep(scan_time)
            res = self.DAQ_LPGBT.read_pattern_checkers(log_dir=None, quiet=True)
            for link in ['Link 0', 'Link 1']:
                for channel in range(24):
                    if res[link]['UPCNT'][channel]['error'][0] == 0:
                        print ("Found uplink alignment for %s, channel %s: %s"%(link, channel, shift))
                        alignment[link][channel] = shift

        # Reset alignment to default values for the channels where no good alignment has been found
        print ("Now setting uplink alignment to optimal values (default values if no good alignment was found)")
        for channel in range(24):
            self.DAQ_LPGBT.set_uplink_alignment(alignment['Link 0'][channel], channel, quiet=True)
            if self.trigger:
                self.TRIG_LPGBT.set_uplink_alignment(alignment['Link 1'][channel], channel, quiet=True)

        return alignment

    def status(self):
        print("Readout Board %s LPGBT Link Status:" % self.rb)
        print("{:<8}{:<8}{:<50}{:<8}".format("Address", "Perm.", "Name", "Value"))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.READY" % self.rb), use_color=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.READY" % self.rb), use_color=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.TRIGGER.UPLINK.READY" % self.rb), use_color=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.TRIGGER.UPLINK.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)

    def configure(self):

        ## DAQ
        #for i in range(28):
        #    self.DAQ_LPGBT.set_uplink_alignment(1, i)  # was 2 for daq loopback. does this behave stochastically?

        self.DAQ_LPGBT.configure_gpio_outputs()
        self.DAQ_LPGBT.initialize()
        self.DAQ_LPGBT.config_eport_dlls()
        self.DAQ_LPGBT.configure_eptx()
        self.DAQ_LPGBT.configure_eprx()

        ## Trigger
        #for i in range(28):
        #    self.TRIG_LPGBT.set_uplink_alignment(5, i) # 4 for trigger loopback

        #self.TRIG_LPGBT.configure_gpio_outputs()
        #self.TRIG_LPGBT.initialize()
        #self.TRIG_LPGBT.config_eport_dlls()
        #self.TRIG_LPGBT.configure_eptx()
        #self.TRIG_LPGBT.configure_eprx()

        _ = self.find_uplink_alignment()

        # SCA init
        self.sca_hard_reset()
        self.sca_setup()
        self.SCA.reset()
        self.SCA.connect()

    def read_temp(self, verbose=0):
        # high level function to read all the temperature sensors
        
        adc_7    = self.DAQ_LPGBT.read_adc(7)/2**10
        adc_in29 = self.SCA.read_adc(29)/2**12
        v_ref    = self.DAQ_LPGBT.read_dac()
        t_SCA    = self.SCA.read_temp()  # internal temp from SCA

        if v_ref>0:
            t1 = get_temp(adc_7, v_ref, 10000, 25, 10000, 3900)  # this comes from the lpGBT ADC
            t2 = get_temp(adc_in29, v_ref, 10000, 25, 10000, 3900)  # this comes from the SCA ADC

            if verbose>0:
                print ("\nV_ref is set to: %.3f V"%v_ref)
                print ("\nTemperature on RB RT1 is: %.3f C"%t1)
                print ("Temperature on RB RT2 is: %.3f C"%t2)
                print ("Temperature on RB SCA is: %.3f C"%t_SCA)
        else:
            print ("V_ref found to be 0. Exiting.")
            return {'t_SCA': t_SCA}

        return {'t1': t1, 't2': t2, 't_SCA': t_SCA}
