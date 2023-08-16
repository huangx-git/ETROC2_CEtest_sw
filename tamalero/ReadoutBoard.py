import os
from tamalero.LPGBT import LPGBT
from tamalero.SCA import SCA
from tamalero.utils import get_temp, chunk, get_temp_direct, get_config
from tamalero.VTRX import VTRX
from tamalero.utils import read_mapping
from tamalero.colors import red, green

try:
    from tabulate import tabulate
except ModuleNotFoundError:
    print ("Package `tabulate` not found.")

from time import sleep

class ReadoutBoard:

    def __init__(self, rb=0, trigger=True, flavor='small', kcu=None, config='default'):
        '''
        create a readout board.
        trigger: if true, also configure a trigger lpGBT
        '''
        self.rb = rb
        self.flavor = flavor
        self.ver = 2
        self.config = config

        self.trigger = trigger
        self.DAQ_LPGBT = LPGBT(rb=rb, flavor=flavor, kcu=kcu, config=self.config)
        self.VTRX = VTRX(self.DAQ_LPGBT)
        # This is not yet recommended:
        #for adr in [0x06, 0x0A, 0x0E, 0x12]:
        #    self.VTRX.wr_adr(adr, 0x20)
        self.SCA = SCA(rb=rb, flavor=flavor, ver=self.DAQ_LPGBT.ver, config=self.config)

        if kcu != None:
            self.kcu = kcu
            self.kcu.readout_boards.append(self)
            self.DAQ_LPGBT.configure()
            if self.DAQ_LPGBT.ver == 1:
                self.ver = 2
                self.SCA.update_ver(self.ver)
                self.DAQ_LPGBT.update_ver(self.ver-1)  #  FIXME we need to disentangle lpGBT version from RB version
            elif self.DAQ_LPGBT.ver == 0:
                self.ver = 1
                self.SCA.update_ver(self.ver)
                self.DAQ_LPGBT.update_ver(self.ver-1)  # FIXME we need to disentangle lpGBT version from RB version
            self.SCA.connect_KCU(kcu)

        self.configuration = get_config(self.config, version=f'v{self.ver}')

    def get_trigger(self):
        # Self-check if a trigger lpGBT is present, if trigger is not explicitely set to False
        sleep(0.5)
        try:
            test_read = self.DAQ_LPGBT.I2C_read(reg=0x0, master=2, slave_addr=0x70, verbose=False)
        except TimeoutError:
            test_read = None
        if test_read is not None and self.trigger:
            print ("Found trigger lpGBT, will configure it now.")
            self.trigger = True
            print (" > Enabling VTRX channel for trigger lpGBT")
            self.VTRX.enable(ch=1)
            sleep(1)
        elif test_read is None:
            print ("No trigger lpGBT found.")
            self.trigger = False
        else:
            print ("Trigger lpGBT was found, but will not be added.")

        if self.trigger:
            self.TRIG_LPGBT = LPGBT(rb=self.rb, flavor=self.flavor, trigger=True, master=self.DAQ_LPGBT, kcu=self.kcu, config=self.config)


    def connect_KCU(self, kcu):
        self.kcu = kcu
        self.DAQ_LPGBT.connect_KCU(kcu)
        self.SCA.connect_KCU(kcu)

    def set_elink_width(self, width=320):
        widths = {320:1, 640:2, 1280:3}
        self.kcu.write_node("READOUT_BOARD_%d.ELINK_WIDTH"%self.rb, widths[width]+1)
        for i in range(7):
            # set banks to 320 Mbps (1) or 640 Mbps (2)
            self.DAQ_LPGBT.wr_reg("LPGBT.RWF.EPORTRX.EPRX%dDATARATE" % i, widths[width])

    def sca_setup(self, verbose=False):
        # should this live here? I suppose so...
        for reg in self.DAQ_LPGBT.ec_config:
            if verbose:
                print(f"{reg}: {self.DAQ_LPGBT.ec_config[reg]}")
            self.DAQ_LPGBT.wr_reg(reg, self.DAQ_LPGBT.ec_config[reg])

    def sca_hard_reset(self):
        # should this live here? I suppose so...
        bit = 0
        self.DAQ_LPGBT.set_gpio(bit, 0)
        sleep(0.1)
        self.DAQ_LPGBT.set_gpio(bit, 1)
        sleep(0.1)

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
        nodes = list(map (lambda x : "READOUT_BOARD_%s.LPGBT." % self.rb + x,
                          ("DOWNLINK.READY",
                      "UPLINK_0.READY",
                      "UPLINK_0.FEC_ERR_CNT",
                      "UPLINK_1.READY",
                      "UPLINK_1.FEC_ERR_CNT",)))
        for node in nodes:
            val = self.kcu.read_node(node)
            err = 0
            err |= ("READY" in node and val != 1)
            err |= ("FEC_ERR_CNT" in node and val != 0)
            if err:
                self.kcu.print_reg(self.kcu.hw.getNode(node), use_color=True, invert=True)

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
            self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.UPLINK_0.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)
            self.kcu.print_reg(self.kcu.hw.getNode("READOUT_BOARD_%s.LPGBT.UPLINK_1.FEC_ERR_CNT" % self.rb), use_color=True, invert=True)
        return {
            'DAQ': self.kcu.read_node("READOUT_BOARD_%s.LPGBT.UPLINK_0.FEC_ERR_CNT" % self.rb).value(),
            'TRIGGER': self.kcu.read_node("READOUT_BOARD_%s.LPGBT.UPLINK_1.FEC_ERR_CNT" % self.rb).value()
        }

    def reset_FEC_error_count(self, quiet=False):
        if not quiet:
            print("Error counts before reset:")
            self.get_FEC_error_count()
        self.kcu.write_node("READOUT_BOARD_%s.LPGBT.FEC_ERR_RESET" % self.rb, 0x1)
        if not quiet:
            print("Error counts after reset:")
            self.get_FEC_error_count()

    def enable_rhett(self):
        self.DAQ_LPGBT.set_gpio(3, 1)

    def disable_rhett(self):
        self.DAQ_LPGBT.set_gpio(3, 1)

    def bad_boy(self, m=1):
        for x in range(60):
            self.DAQ_LPGBT.set_gpio(3, 1)
            sleep(m*(0.000 + 0.0005*x))
            self.DAQ_LPGBT.set_gpio(3, 0)
            sleep(m*0.005)
        self.DAQ_LPGBT.set_gpio(3, 1)
        sleep(1)
        for x in range(60):
            self.DAQ_LPGBT.set_gpio(3, 1)
            sleep(m*(0.030 - 0.0005*x))
            self.DAQ_LPGBT.set_gpio(3, 0)
            sleep(m*0.005)
        self.DAQ_LPGBT.set_gpio(3, 0)
        sleep(1)

    def configure(self, alignment=None, data_mode=False, etroc='ETROC1', verbose=False):

        # configure the VTRX
        self.VTRX.configure(trigger=self.trigger)

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
        #self.
        self.sca_hard_reset()
        self.sca_setup(verbose=verbose)
        self.SCA.reset()
        self.SCA.connect()
        try:
            print("version in SCA", self.SCA.ver)
            print("config in SCA", self.SCA.config)
            self.SCA.config_gpios()  # this sets the directions etc according to the mapping
        except TimeoutError:
            print ("SCA config failed. Will continue without SCA.")
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
                #self.VTRX.reset(toggle_channels=[0])
                self.VTRX.reset()
            else:
                print ("Don't know how to reset VTRX version", self.VTRX.ver)
            self.VTRX.configure(trigger=trigger)
            self.DAQ_LPGBT.reset_daq_mgts()
            self.DAQ_LPGBT.power_up_init()

        self.reset_FEC_error_count(quiet=True)

    def reset_problematic_links(self, max_retries=10, allow_bad_links=False, verbose=False):
        '''
        First check DAQ link, then trigger link.
        '''
        for link in ['DAQ', 'Trigger'] if self.trigger else ['DAQ']:
            for i in range(max_retries):
                if link == 'DAQ':
                    good_link = self.DAQ_LPGBT.link_status(verbose=False)
                else:
                    good_link = self.TRIG_LPGBT.link_status(verbose=False)
                if good_link:
                    if verbose:
                        print (f"No FEC errors detected on {link} link")
                    break
                else:
                    if self.ver == 1:
                        pass
                    else:
                        self.reset_link(trigger = (link=='Trigger'))
                if i+2 > max_retries:
                    if allow_bad_links:
                        print (f"{link} link does not have a stable connection. Ignoring.")
                    else:
                        raise RuntimeError(f"{link} link does not have a stable connection after {max_retries} retries")
    
    #creates dict for mux64 testboard pins
    def init_mux_tb_dict(self):
        self.mux64_tb_dict = read_mapping(os.path.expandvars('$TAMALERO_BASE/configs/MUX64_testboard_mapping.yaml'), 'mux64_testboard')
        return

    # Uses MUX64-testboard dictionary to convert integar to voltage
    def volt_conver_mux64(self,num,ch):
        voltage = (num / (2**12 - 1) ) * self.mux64_tb_dict[ch]['conv']
        return voltage
    
    def read_mux_test_board(self, ch):
        #checks to see RB mapping version (RB ver = 1, SCA ver = RB.ver + 1)
        assert self.SCA.ver in [2], f"MUX64 testboard only works with 2v RB\nRB 1v detected"

        #checks to see if MUX64 testboard dict has already been initialized
        if not self.mux64_tb_dict:
            self.init_mux_tb_dict()

        #channel select
        s0 = (ch & 0x01)
        s1 = (ch & 0x02) >> 1
        s2 = (ch & 0x04) >> 2
        s3 = (ch & 0x08) >> 3
        s4 = (ch & 0x10) >> 4
        s5 = (ch & 0x20) >> 5

        self.SCA.set_gpio(0x16, s0) #mod_d08
        self.SCA.set_gpio(0x19, s1) #mod_d09
        self.SCA.set_gpio(0x13, s2) #mod_d10
        self.SCA.set_gpio(0x10, s3) #mod_d11
        self.SCA.set_gpio(0x0A, s4) #mod_d12
        self.SCA.set_gpio(0x04, s5) #mod_d13

        #read integar value and covert it to a voltge
        integer_volt = self.SCA.read_adc(0x12)
        gi = self.volt_conver_mux64(integer_volt,ch)

        return volt
    
    def read_all_mux64_data(self, show = False):
        table=[]
        v_data=[]
        for i in self.mux64_tb_dict.keys():
            if self.mux64_tb_dict[i]['terminal_input']:
                volt=self.read_mux_test_board(i)
                v_data.append(volt)
            else:
                volt=None
                v_data.append(volt)
            sig_name=self.mux64_tb_dict[i]['sig_name']
            table.append([i, volt, sig_name])
        
        if (show):
            print(tabulate(table, headers=["Channel","Voltage", "Sig_Name"],  tablefmt="simple_outline"))

        return table

    def read_vtrx_temp(self):

        # vtrx thermistors

        v_ref = self.DAQ_LPGBT.read_dac()
        if self.ver == 1:
            #current_rt1 = self.DAQ_LPGBT.set_current_dac_uA(0)  # make sure the current source is turned OFF in ver 1
            rt_vtrx_voltage = self.DAQ_LPGBT.read_adc(0)/(2**10-1) # FIXME: 0 should not be hardcoded
            return get_temp(rt_vtrx_voltage, v_ref, 10000, 25, 10000, 3900)  # FIXME this uses the wrong thermistor, ignore value.
            #return -1.0
        elif self.ver == 2:
            current_vtrx    = self.DAQ_LPGBT.set_current_dac_uA(600)
            rt_vtrx_voltage = self.DAQ_LPGBT.read_adc(0)/(2**10-1) # FIXME: 0 should not be hardcoded
            return get_temp_direct(rt_vtrx_voltage, current_vtrx, thermistor="NCP03XM102E05RL")  # this comes from the lpGBT ADC (VTRX TH)
        else:
            raise Exception("Unknown lpgbt version")

    def read_rb_thermistor(self, rt):

        # read voltage reference; some temperature readings depend on it
        v_ref = self.DAQ_LPGBT.read_dac()
        if v_ref==0 and ((rt==1 and self.ver==1) or rt==2):
            raise Exception("Read temperature called with VREF configured as 0V. VREF must be configured to read the temperatures.")

        if rt==1:

            if self.ver == 1:
                # This uses the DAC output for current so just read the voltage
                #current_rt1 = self.DAQ_LPGBT.set_current_dac_uA(0)  # make sure the current source is turned OFF in ver 1
                rt1_voltage = self.DAQ_LPGBT.read_adc(7)/(2**10-1) # FIXME: 7 should not be hardcoded
                return get_temp(rt1_voltage, v_ref, 10000, 25, 10000, 3900)  # this comes from the lpGBT ADC
            elif self.ver == 2:
                # Set the DAC current then read the voltage
                current_rt1 = self.DAQ_LPGBT.set_current_dac_uA(50)
                rt1_voltage = self.DAQ_LPGBT.read_adc(7)/(2**10-1) # FIXME: 7 should not be hardcoded
                return get_temp_direct(rt1_voltage, current_rt1, thermistor="NTCG063JF103FTB")  # this comes from the lpGBT ADC
            else:
                raise Exception("Unknown lpgbt version")

        elif rt==2:

            rt2_voltage = self.SCA.read_adc(29)/(2**12-1) # FIXME: 29 should not be hardcoded

            if self.ver == 1:
                # https://www.digikey.com/en/products/detail/tdk-corporation/NTCG063UH103HTBX/8565486
                return get_temp(rt2_voltage, v_ref, 10000, 25, 10000, 3900)  # this comes from the SCA ADC
            elif self.ver == 2:
                # https://www.digikey.com/en/products/detail/tdk-corporation/NTCG063JF103FTB/5872743
                return get_temp(rt2_voltage, v_ref, 10000, 25, 10000, 3380)  # this comes from the SCA ADC
            else:
                raise Exception("Unknown lpgbt version")

        else:
            raise Exception(f"Attempt to read unknown thermistor rt={rt}")

    def read_temp(self, verbose=False):

        """
        read all the temperature sensors
        """

        # internal temp from SCA
        t_sca = self.SCA.read_temp()
        t_vtrx = self.read_vtrx_temp()
        t_rt1 = self.read_rb_thermistor(1)
        t_rt2 = self.read_rb_thermistor(2)

        if verbose:
            print ("\nTemperature on RB RT1 is: %.1f C" % t_rt1)
            print ("Temperature on RB RT2 is: %.1f C" % t_rt2)
            print ("Temperature on RB SCA is: %.1f C" % t_sca)
            if self.ver==2:
                print ("Temperature on RB VTRX is: %.1f C" % t_vtrx)

        return {'t1': t_rt1, 't2': t_rt2, 't_SCA': t_sca, 't_VTRX': t_vtrx}

    def etroc_locked(self, elink, slave=False):
        if slave:
            locked = self.kcu.read_node(f"READOUT_BOARD_{self.rb}.ETROC_LOCKED_SLAVE").value()
        else:
            locked = self.kcu.read_node(f"READOUT_BOARD_{self.rb}.ETROC_LOCKED").value()

        return ((locked & (1 << elink)) >> elink) == True

    def disable_etroc_readout(self, elink, slave=False):
        if slave:
            disabled = self.kcu.read_node(f"READOUT_BOARD_{self.rb}.ETROC_DISABLE_SLAVE").value()
            to_disable = disabled | (1 << elink)
            self.kcu.write_node(f"READOUT_BOARD_{self.rb}.ETROC_DISABLE_SLAVE", to_disable)
        else:
            disabled = self.kcu.read_node(f"READOUT_BOARD_{self.rb}.ETROC_DISABLE").value()
            to_disable = disabled | (1 << elink)
            self.kcu.write_node(f"READOUT_BOARD_{self.rb}.ETROC_DISABLE", to_disable)

    def enable_etroc_readout(self, slave=False):
        if slave:
            self.kcu.write_node(f"READOUT_BOARD_{self.rb}.ETROC_DISABLE_SLAVE", 0)
        else:
            self.kcu.write_node(f"READOUT_BOARD_{self.rb}.ETROC_DISABLE", 0)

    def reset_data_error_count(self):
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.PACKET_CNT_RESET", 0x1)
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.ERR_CNT_RESET", 0x1)
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.DATA_CNT_RESET", 0x1)

    def read_filler_rate(self, elink, slave=False):
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_ELINK_SEL0", elink)
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_LPGBT_SEL0", 1 if slave else 0)
        return self.kcu.read_node(f"READOUT_BOARD_{self.rb}.FILLER_RATE").value()

    def read_packet_count(self, elink, slave=False):
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_ELINK_SEL0", elink)
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_LPGBT_SEL0", 1 if slave else 0)
        return self.kcu.read_node(f"READOUT_BOARD_{self.rb}.PACKET_CNT").value()

    def read_error_count(self, elink, slave=False):
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_ELINK_SEL0", elink)
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_LPGBT_SEL0", 1 if slave else 0)
        return self.kcu.read_node(f"READOUT_BOARD_{self.rb}.ERROR_CNT").value()

    def read_data_count(self, elink, slave=False):
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_ELINK_SEL0", elink)
        self.kcu.write_node(f"READOUT_BOARD_{self.rb}.FIFO_LPGBT_SEL0", 1 if slave else 0)
        return self.kcu.read_node(f"READOUT_BOARD_{self.rb}.DATA_CNT").value()

    def get_link_status(self, elink, slave=False, verbose=True):
        expected_filler_rate = 16500000

        print(f"- Status of link {elink}")
        locked = self.etroc_locked(elink, slave=slave)

        filler_rate = self.read_filler_rate(elink, slave=slave)
        error_count = self.read_error_count(elink, slave=slave)
        packet_count = self.read_packet_count(elink, slave=slave)
        data_count = self.read_data_count(elink, slave=slave)

        if verbose:
            colored = green if (locked) else red
            print(colored("{:20}{:10}".format("Locked", locked)))
            colored = green if (filler_rate > expected_filler_rate) else red
            print(colored("{:20}{:10}".format("Filler rate", filler_rate)))
            colored = green if (error_count < 1) else red
            print(colored("{:20}{:10}".format("Error count", error_count)))
            print("{:20}{:10}".format("Packet count", packet_count))
            print("{:20}{:10}".format("Data count", data_count))

            if filler_rate < expected_filler_rate:
                print("Filler rate is low. Try resetting PLL and FC of the ETROC.")

        return locked & (filler_rate > expected_filler_rate) & (error_count < 1)
