from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard

from tamalero.SCA import SCA_CONTROL

if __name__ == '__main__':

    kcu = KCU(name="my_device",
              ipb_path="ipbusudp-2.0://192.168.0.10:50001",
              adr_table="address_table/etl_test_fw.xml")

    kcu.status()

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=False))

    rb_0.configure()
    rb_0.DAQ_LPGBT.status()

    init_sca = True
    if init_sca:
        rb_0.sca_hard_reset()
        rb_0.sca_setup()
        rb_0.SCA.reset()
        rb_0.SCA.connect()

    from tamalero.utils import get_temp
    
    adc_7 = rb_0.DAQ_LPGBT.read_adc(7)/2**10
    dac = rb_0.DAQ_LPGBT.read_dac()

    if dac>0:
        print ("\nTemperature on RB RT1 is: %.3f C"%get_temp(adc_7, dac, 10000, 25, 10000, 3900))

    if rb_0.DAQ_LPGBT.rd_reg("LPGBT.RWF.CALIBRATION.VREFENABLE"):
        adc_in29 = rb_0.SCA.read_adc(29)/2**12
        print ("\nTemperature on RB RT2 is: %.3f C"%get_temp(adc_in29, 1.0, 10000, 25, 10000, 3900))

    

