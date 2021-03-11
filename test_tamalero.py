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


    from tamalero.utils import get_temp
    
    if rb_0.DAQ_LPGBT.rd_reg("LPGBT.RWF.CALIBRATION.VREFENABLE"):
        dac_29 = rb_0.SCA.ADC_read(29)/2**12
        print ("\nTemperature on RB is: %.3f C"%get_temp(dac_29, 1.0, 10000, 25, 10000, 3900))
