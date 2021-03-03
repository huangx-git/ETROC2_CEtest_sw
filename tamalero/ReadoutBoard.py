from tamalero.LPGBT import LPGBT
from tamalero.SCA import SCA


class ReadoutBoard:

    def __init__(self, rb=0, trigger=True):
        '''
        create a readout board.
        trigger: if true, configure a trigger lpGBT
        '''
        self.rb = rb

        self.trigger = trigger

        self.DAQ_LPGBT = LPGBT(rb=rb)
        self.DAQ_LPGBT.parse_xml('address_table/lpgbt.xml')

        self.SCA = SCA(rb=rb)

    def connect_KCU(self, kcu):
        self.kcu = kcu
        self.DAQ_LPGBT.connect_KCU(kcu)
        self.SCA.connect_KCU(kcu)

    def configure(self):

        # use n for loopback, 0 for internal data generators
        for i in range(28):
            self.DAQ_LPGBT.set_daq_uplink_alignment(2, i)  # 2 for daq loopback
            # set_trig_uplink_alignment(4, i) # 4 for trigger loopback

        self.DAQ_LPGBT.configure_gpio_outputs()
        self.DAQ_LPGBT.initialize()
        self.DAQ_LPGBT.config_eport_dlls()
