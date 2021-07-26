import os
from tamalero.LPGBT import LPGBT
from tamalero.SCA import SCA
from tamalero.utils import get_temp


class ReadoutBoard:

    def __init__(self, rb=0, trigger=True, flavor='small'):
        '''
        create a readout board.
        trigger: if true, configure a trigger lpGBT
        '''
        self.rb = rb
        self.flavor = flavor

        self.trigger = trigger

        self.DAQ_LPGBT = LPGBT(rb=rb, flavor=flavor)
        self.DAQ_LPGBT.parse_xml(os.path.expandvars('$TAMALERO_BASE/address_table/lpgbt.xml'))

        self.SCA = SCA(rb=rb, flavor=flavor)

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

    def configure(self):

        # use n for loopback, 0 for internal data generators
        for i in range(28):
            self.DAQ_LPGBT.set_daq_uplink_alignment(2, i)  # 2 for daq loopback
            # set_trig_uplink_alignment(4, i) # 4 for trigger loopback

        self.DAQ_LPGBT.configure_gpio_outputs()
        self.DAQ_LPGBT.initialize()
        self.DAQ_LPGBT.config_eport_dlls()
        self.DAQ_LPGBT.configure_eptx()
        self.DAQ_LPGBT.configure_eprx()



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
        t_SCA    = self.SCA.read_temp()

        if v_ref>0:
            t1 = get_temp(adc_7, v_ref, 10000, 25, 10000, 3900)
            t2 = get_temp(adc_in29, v_ref, 10000, 25, 10000, 3900)

            if verbose>0:
                print ("\nV_ref is set to: %.3f V"%v_ref)
                print ("\nTemperature on RB RT1 is: %.3f C"%t1)
                print ("Temperature on RB RT2 is: %.3f C"%t2)
                print ("Temperature on RB SCA is: %.3f C"%t_SCA)
        else:
            print ("V_ref found to be 0. Exiting.")
            return {'t_SCA': t_SCA}

        return {'t1': t1, 't2': t2, 't_SCA': t_SCA}
