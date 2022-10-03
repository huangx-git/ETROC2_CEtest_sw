import os
from tamalero.LPGBT import LPGBT
from tamalero.SCA import SCA
from tamalero.utils import get_temp, chunk
from tamalero.VTRX import VTRX

from time import sleep

class ReadoutBoard:

    def __init__(self, rb=0, trigger=True, flavor='small', kcu=None):
        '''
        create a readout board.
        trigger: if true, also configure a trigger lpGBT
        '''
        self.rb = rb
        self.flavor = flavor

        self.trigger = trigger
        self.DAQ_LPGBT = LPGBT(rb=rb, flavor=flavor, kcu=kcu)
        self.DAQ_LPGBT.parse_xml(self.DAQ_LPGBT.ver)
        self.VTRX = VTRX(self.DAQ_LPGBT)
        # This is not yet recommended:
        #for adr in [0x06, 0x0A, 0x0E, 0x12]:
        #    self.VTRX.wr_adr(adr, 0x20)

        self.SCA = SCA(rb=rb, flavor=flavor)

        if kcu != None:
            self.kcu = kcu
            self.kcu.readout_boards.append(self)
            self.DAQ_LPGBT.connect_KCU(kcu)
            self.SCA.connect_KCU(kcu)

        if not self.kcu.dummy:
            self.DAQ_LPGBT.get_version()

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
            self.TRIG_LPGBT.connect_KCU(self.kcu)
            self.TRIG_LPGBT.get_version()
            self.TRIG_LPGBT.parse_xml(self.TRIG_LPGBT.ver)
            print ("Connected trigger lpGBT to KCU.")
            self.TRIG_LPGBT.callibrate_adc()


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

    def find_uplink_alignment(self, scan_time=0.01, default=0, data_mode=False, etroc='ETROC1'):  # default scan time of 0.01 is enough
        # TODO: check the FEC mode and set the number of links appropriately
        n_links = 24  #  NOTE: there are 28 e-links if the board is in FEC5 mode, but we are operating in FEC12 where there are only 24
        print ("Scanning for uplink alignment")
        print ("In data mode:", data_mode)
        alignment = {}
        inversion = {} # also scan for inversion
        # make alignment dict
        for link in ['Link 0', 'Link 1']:
            alignment[link] = {i:default for i in range(n_links)}
            inversion[link] = {i:0x02 for i in range(n_links)}

        # TODO: the scan should check the pattern checkers first, and skip the scan for any where the pattern check is already ok

        # now, scan
        if data_mode:
            for channel in range(n_links):
                res_daq = 0
                res_trig = 0
                for inv in [False, True]:
                    for shift in range(8):
                        self.DAQ_LPGBT.set_uplink_alignment(channel, shift, quiet=True)
                        self.DAQ_LPGBT.set_uplink_invert(channel, inv)
                        tmp = self.check_data_integrity(channel=channel, etroc=etroc, trigger=False)
                        if tmp>res_daq and tmp>1:  # NOTE: sometimes we find a random good word
                            print ("Found improved uplink alignment for Link 0, channel %s: %s, inverted: %s"%(channel, shift, inv))
                            alignment['Link 0'][channel] = shift
                            inversion['Link 0'][channel] = inv
                            res_daq = tmp
                        if self.trigger:
                            self.TRIG_LPGBT.set_uplink_alignment(channel, shift, quiet=True)
                            self.TRIG_LPGBT.set_uplink_invert(channel, inv)
                            tmp = self.check_data_integrity(channel=channel, etroc=etroc, trigger=True)
                            if tmp>res_trig and tmp>1:  # NOTE: sometimes we find a random good word
                                print ("Found improved uplink alignment for Link 1, channel %s: %s, inverted: %s"%(channel, shift, inv))
                                alignment['Link 1'][channel] = shift
                                inversion['Link 1'][channel] = inv
                                res_trig = tmp
        else:
            for inv in [False, True]:
                for shift in range(8):
                    for channel in range(n_links):
                        self.DAQ_LPGBT.set_uplink_alignment(channel, shift, quiet=True)
                        self.DAQ_LPGBT.set_uplink_invert(channel, inv)
                        if self.trigger:
                            self.TRIG_LPGBT.set_uplink_alignment(channel, shift, quiet=True)
                            self.TRIG_LPGBT.set_uplink_invert(channel, inv)
                    self.DAQ_LPGBT.set_uplink_group_data_source("normal")  # actually needed??
                    self.DAQ_LPGBT.set_downlink_data_src('upcnt')
                    self.DAQ_LPGBT.reset_pattern_checkers()
                    sleep(scan_time)
                    res = self.DAQ_LPGBT.read_pattern_checkers(log_dir=None, quiet=True)
                    for link in ['Link 0', 'Link 1']:
                        for channel in range(n_links):
                            if res[link]['UPCNT'][channel]['error'][0] == 0:
                                print ("Found uplink alignment for %s, channel %s: %s, inverted: %s"%(link, channel, shift, inv))
                                alignment[link][channel] = shift
                                inversion[link][channel] = inv

        # Reset alignment to default values for the channels where no good alignment has been found
        print ("Now setting uplink alignment to optimal values (default values if no good alignment was found)")
        for channel in range(n_links):
            self.DAQ_LPGBT.set_uplink_alignment(channel, alignment['Link 0'][channel], quiet=True)
            self.DAQ_LPGBT.set_uplink_invert(channel, inversion['Link 0'][channel])
            if self.trigger:
                self.TRIG_LPGBT.set_uplink_alignment(channel, alignment['Link 1'][channel], quiet=True)
                self.TRIG_LPGBT.set_uplink_invert(channel, inversion['Link 1'][channel])

        return alignment

    def dump_uplink_alignment(self, n_links=24):

        alignment = {
            'daq': {
                'alignment': {},
                'inversion': {},
            },
            'trigger': {
                'alignment': {},
                'inversion': {},
            }
        }

        for i in range(n_links):
            alignment['daq']['alignment'][i] = self.DAQ_LPGBT.get_uplink_alignment(i)
            alignment['daq']['inversion'][i] = self.DAQ_LPGBT.get_uplink_invert(i)

            if self.trigger:
                alignment['trigger']['alignment'][i] = self.TRIG_LPGBT.get_uplink_alignment(i)
                alignment['trigger']['inversion'][i] = self.TRIG_LPGBT.get_uplink_invert(i)

        return alignment

    def load_uplink_alignment(self, alignment, n_links=24):

        for i in range(n_links):
            self.DAQ_LPGBT.set_uplink_alignment(i ,alignment['daq']['alignment'][i])
            self.DAQ_LPGBT.set_uplink_invert(i, alignment['daq']['inversion'][i])

            if self.trigger:
                self.TRIG_LPGBT.set_uplink_alignment(i, alignment['trigger']['alignment'][i])
                self.TRIG_LPGBT.set_uplink_invert(i, alignment['trigger']['inversion'][i])

    def status(self):
        print("Readout Board %s LPGBT Link Status:" % self.rb)
        print("{:<8}{:<8}{:<50}{:<8}".format("Address", "Perm.", "Name", "Value"))
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.READY" % self.rb), use_color=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.READY" % self.rb), use_color=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.TRIGGER.UPLINK.READY" % self.rb), use_color=True)
        self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.TRIGGER.UPLINK.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)

    def check_data_integrity(self, channel=0, etroc='ETROC1', trigger=False):
        '''
        Not sure where this function should live.
        It's not necessarily a part of the RB.
        '''
        from tamalero.FIFO import FIFO
        from tamalero.DataFrame import DataFrame
        df = DataFrame(etroc)
        lpgbt = 1 if trigger else 0
        fifo = FIFO(self, links=[{'elink': channel, 'lpgbt': lpgbt}], ETROC=etroc,)
        fifo.set_trigger(
            df.get_trigger_words(),
            df.get_trigger_masks(),
        )
        fifo.reset(l1a=True)
        n_header = 0
        n_trailer = 0
        data  = []
        for i in range(1):
            data += fifo.giant_dump(3000, align=False, format=False)  # + ['35', '55'] + fifo.giant_dump(3000)
            fifo.reset(l1a=True)

        good_counter = 0
        for word in data:
            word_type, _ = df.read(word, quiet=True)
            if word_type == None:
                return 0
            elif word_type in ['header', 'filler']:
                # ETROC2 data and filler definitions are so weak, it's easy to accidentially find them.
                good_counter += 1

        return good_counter


    def get_FEC_error_count(self, quiet=False):
        if not quiet:
            print("{:<8}{:<8}{:<50}{:<8}".format("Address", "Perm.", "Name", "Value"))
            self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)
            self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.TRIGGER.UPLINK.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)
        return {
            'DAQ': self.kcu.read_node("READOUT_BOARD_%s.LPGBT.DAQ.UPLINK.FEC_ERR_CNT" % self.rb).value(),
            'TRIGGER': self.kcu.read_node("READOUT_BOARD_%s.LPGBT.TRIGGER.UPLINK.FEC_ERR_CNT" % self.rb).value()
        }

    def reset_FEC_error_count(self, quiet=False):
        if not quiet:
            print("Error counts before reset:")
            self.get_FEC_error_count()
        self.kcu.write_node("READOUT_BOARD_%s.LPGBT.FEC_ERR_RESET" % self.rb, 0x1)
        if not quiet:
            print("Error counts after reset:")
            self.get_FEC_error_count()

    def configure(self, alignment=None, data_mode=False, etroc='ETROC1'):

        ## DAQ
        #for i in range(28):
        #    self.DAQ_LPGBT.set_uplink_alignment(1, i)  # was 2 for daq loopback. does this behave stochastically?

        self.DAQ_LPGBT.configure_gpio_outputs()
        self.DAQ_LPGBT.initialize()
        self.DAQ_LPGBT.config_eport_dlls()
        self.DAQ_LPGBT.configure_eptx()
        self.DAQ_LPGBT.configure_eprx()

        # configure the VTRX
        self.VTRX.configure(trigger=self.trigger)

        ## Trigger
        #for i in range(28):
        #    self.TRIG_LPGBT.set_uplink_alignment(5, i) # 4 for trigger loopback

        #self.TRIG_LPGBT.configure_gpio_outputs()
        #self.TRIG_LPGBT.initialize()
        #self.TRIG_LPGBT.config_eport_dlls()
        #self.TRIG_LPGBT.configure_eptx()
        #self.TRIG_LPGBT.configure_eprx()

        # the logic here is as follows:
        # dict -> load the provided alignment
        # none -> rerun alignment scan
        # anything else (e.g. False) -> don't touch the uplink alignment
        if isinstance(alignment, dict):
            self.load_uplink_alignment(alignment)
        elif alignment is None:
            _ = self.find_uplink_alignment(data_mode=data_mode, etroc=etroc)
        else:
            pass

        # SCA init
        self.sca_hard_reset()
        self.sca_setup()
        self.SCA.reset()
        self.SCA.connect()
        self.SCA.config_gpios()  # this sets the directions etc according to the mapping

        #if self.trigger:
        #    self.DAQ_LPGBT.reset_trigger_mgts() 

        #sleep(0.5)

    def reset_link(self, trigger=False):
        '''
        Resets the links entirely, different procedure is necessary for production / prototype version of VTRX
        '''
        if trigger:
            if self.VTRX.ver == 'production':
                self.VTRX.reset(toggle_channels=[1])
            elif self.VTRX.ver == 'prototype':
                self.VTRX.reset(toggle_channels=[1])
            else:
                print ("Don't know how to reset VTRX version", self.VTRX.ver)
            self.VTRX.configure(trigger=trigger)
            self.DAQ_LPGBT.reset_trigger_mgts()
            self.TRIG_LPGBT.power_up_init(verbose=False)
        else:
            if self.VTRX.ver == 'production':
                self.VTRX.reset()
            elif self.VTRX.ver == 'prototype':
                self.VTRX.reset(toggle_channels=[0])
            else:
                print ("Don't know how to reset VTRX version", self.VTRX.ver)
            self.VTRX.configure(trigger=trigger)
            self.DAQ_LPGBT.reset_daq_mgts()
            self.DAQ_LPGBT.power_up_init()

        self.reset_FEC_error_count(quiet=True)

    def reset_problematic_links(self, max_retries=10, allow_bad_links=False):
        '''
        First check DAQ link, then trigger link.
        '''
        for link in ['DAQ', 'Trigger'] if self.trigger else ['DAQ']:
            for i in range(max_retries):
                if link == 'DAQ':
                    good_link = self.DAQ_LPGBT.link_status()
                else:
                    good_link = self.TRIG_LPGBT.link_status()
                if good_link:
                    print (f"No FEC errors detected on {link} link")
                    break
                else:
                    self.reset_link(trigger = (link=='Trigger'))
                if i+2 > max_retries:
                    if allow_bad_links:
                        print (f"{link} link does not have a stable connection. Ignoring.")
                    else:
                        raise RuntimeError(f"{link} link does not have a stable connection after {max_retries} retries")

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
