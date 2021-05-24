from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard

from tamalero.SCA import SCA_CONTROL

import time
import random

if __name__ == '__main__':


    import argparse

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--power_up', action='store_true', default=False, help="Do lpGBT power up init?")
    argParser.add_argument('--i2c_temp', action='store_true', default=False, help="Do temp monitoring on I2C?")
    args = argParser.parse_args()


    kcu = KCU(name="my_device",
              ipb_path="ipbusudp-2.0://192.168.0.10:50001",
              adr_table="module_test_fw/address_tables/etl_test_fw.xml")

    kcu.status()

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=False))

    if args.power_up:
        rb_0.DAQ_LPGBT.power_up_init()

    rb_0.configure()

    rb_0.DAQ_LPGBT.status()

    print("reading ADC values:")
    rb_0.SCA.read_adcs()

    from tamalero.utils import get_temp
    
    # Low level reading of temperatures
    # Read ADC channel 7 on DAQ lpGBT
    adc_7 = rb_0.DAQ_LPGBT.read_adc(7)/(2**10-1)

    # Read ADC channel 29 on GBT-SCA
    adc_in29 = rb_0.SCA.read_adc(29)/(2**12-1)

    # Check what the lpGBT DAC is set to
    v_ref = rb_0.DAQ_LPGBT.read_dac()
    print ("\nV_ref is set to: %.3f V"%v_ref)

    if v_ref>0:
        print ("\nTemperature on RB RT1 is: %.3f C"%get_temp(adc_7, v_ref, 10000, 25, 10000, 3900))
        print ("Temperature on RB RT2 is: %.3f C"%get_temp(adc_in29, v_ref, 10000, 25, 10000, 3900))

    # High level reading of temperatures
    temp = rb_0.read_temp(verbose=1)

    if args.i2c_temp:

        for i in range(100):
            print ( rb_0.DAQ_LPGBT.read_temp_i2c() )
            time.sleep(1)

    print("Writing and Reading I2C_ctrl register:")
    for n in range(10):
        wr = random.randint(0, 100)
        rb_0.SCA.I2C_write_ctrl(channel=3, data=wr)
        rd = rb_0.SCA.I2C_read_ctrl(channel=3)
        print("write: {} \t read: {}".format(wr, rd))

    print("Testing multi-byte read:")
    multi_out = rb_0.SCA.I2C_read_multi(channel=3, servant = 0x48, nbytes=2)
    print("servant: 0x48, channel: 3, nbytes: 2, output = {}".format(multi_out))
