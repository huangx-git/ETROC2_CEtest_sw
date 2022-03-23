from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import header, make_version_header
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame

from tamalero.SCA import SCA_CONTROL

import time
import random
import sys


if __name__ == '__main__':


    import argparse

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--power_up', action='store_true', default=False, help="Do lpGBT power up init?")
    argParser.add_argument('--reconfigure', action='store_true', default=False, help="Configure the RB electronics: SCA and lpGBT?")
    argParser.add_argument('--adcs', action='store_true', default=False, help="Read ADCs?")
    argParser.add_argument('--i2c_temp', action='store_true', default=False, help="Do temp monitoring on I2C from lpGBT?")
    argParser.add_argument('--i2c_sca', action='store_true', default=False, help="I2C tests on SCA?")
    argParser.add_argument('--run_pattern_checker', action='store_true', default=False, help="Read pattern checker?")
    argParser.add_argument('--reset_pattern_checker', action='store', choices=[None, 'prbs', 'upcnt'], default=None, help="Reset pattern checker?")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--force_no_trigger', action='store_true', help="Never initialize the trigger lpGBT.")
    argParser.add_argument('--read_fifo', action='store', default=-1, help='Read 3000 words from link N')
    argParser.add_argument('--load_alignment', action='store', default=None, help='Load predefined alignment, skips the scan.')
    argParser.add_argument('--etroc', action='store', default="ETROC1", help='Load predefined alignment, skips the scan.')
    args = argParser.parse_args()

    header()

    if args.read_fifo: data_mode = True

    print ("Using KCU at address: %s"%args.kcu)

    kcu = KCU(name="my_device",
              #ipb_path="chtcp-2.0://localhost:10203?target=%s:50001"%args.kcu,
              ipb_path="ipbusudp-2.0://%s:50001"%args.kcu,
              adr_table="module_test_fw/address_tables/etl_test_fw.xml")

    kcu.status()


    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=(not args.force_no_trigger)))

    data = 0xabcd1234
    kcu.write_node("LOOPBACK.LOOPBACK", data)
    if (data != kcu.read_node("LOOPBACK.LOOPBACK")):
        print("No communications with KCU105... quitting")
        sys.exit(0)

    if args.power_up:
        print ("Power up init sequence for: DAQ")
        rb_0.DAQ_LPGBT.power_up_init()
        if (rb_0.DAQ_LPGBT.rd_adr(0x1c5) != 0xa5):
            print(hex(rb_0.DAQ_LPGBT.rd_adr(0x1c5)))
            print ("No communication with DAQ LPGBT... trying to reset DAQ MGTs")
            rb_0.DAQ_LPGBT.reset_daq_mgts()
            rb_0.DAQ_LPGBT.power_up_init()
            #sys.exit(0)
        #rb_0.TRIG_LPGBT.power_up_init()
        rb_0.get_trigger()
        if rb_0.trigger:
            print ("Power up init sequence for: Trigger")
            rb_0.TRIG_LPGBT.power_up_init()
        #rb_0.DAQ_LPGBT.power_up_init_trigger()

    if not hasattr(rb_0, "TRIG_LPGBT"):
        rb_0.get_trigger()

    if args.power_up or args.reconfigure:
        if args.load_alignment is not None:
            from tamalero.utils import load_alignment_from_file
            alignment = load_alignment_from_file(args.load_alignment)
        else:
            alignment = None
        rb_0.configure(alignment=alignment, data_mode=data_mode, etroc=args.etroc)  # this is very slow, especially for the trigger lpGBT.
        if rb_0.trigger:
            rb_0.DAQ_LPGBT.reset_trigger_mgts() 
        time.sleep(1.0)

    res = rb_0.DAQ_LPGBT.get_board_id()
    res['trigger'] = 'yes' if rb_0.trigger else 'no'
    make_version_header(res)

    rb_0.status()

    _ = rb_0.VTRX.status()

    rb_0.DAQ_LPGBT.set_dac(1.0)  # set the DAC / Vref to 1.0V.

    if args.adcs or args.power_up:
        print("\n\nReading GBT-SCA ADC values:")
        rb_0.SCA.read_adcs()

        print("\n\nReading DAQ lpGBT ADC values:")
        rb_0.DAQ_LPGBT.read_adcs()

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

    if args.i2c_sca:

        print("Writing and Reading I2C_ctrl register:")
        for n in range(10):
            wr = random.randint(0, 100)
            rb_0.SCA.I2C_write_ctrl(channel=3, data=wr)
            rd = rb_0.SCA.I2C_read_ctrl(channel=3)
            print("write: {} \t read: {}".format(wr, rd))

        print("Testing multi-byte read:")
        multi_out = rb_0.SCA.I2C_read_multi(channel=3, servant = 0x48, nbytes=2)
        print("servant: 0x48, channel: 3, nbytes: 2, output = {}".format(multi_out))

        print("Testing multi-byte write:")

        write_value = [0x2, 25, (27&240)]
        print("servant: 0x48, channel: 3, nbytes: 2, data:{}".format(write_value))
        rb_0.SCA.I2C_write_multi(write_value, channel=3, servant=0x48)
        read_value = rb_0.SCA.I2C_read_multi(channel=3, servant=0x48, nbytes = 2, reg=0x2)

        if read_value == write_value[1:]:
            print ("write/read successful!")
        print("read value = {}".format(rb_0.SCA.I2C_read_multi(channel=3, servant=0x48, nbytes = 2, reg=0x2)))


    if args.reset_pattern_checker:
        print ("\nResetting the pattern checker.")
        rb_0.DAQ_LPGBT.set_uplink_group_data_source("normal")
        rb_0.DAQ_LPGBT.set_downlink_data_src(args.reset_pattern_checker)
        time.sleep(0.1)
        rb_0.DAQ_LPGBT.reset_pattern_checkers()
        time.sleep(0.1)

    if args.run_pattern_checker:
        print ("\nReading the pattern checker counter. Waiting 1 sec.")
        time.sleep(1)
        rb_0.DAQ_LPGBT.read_pattern_checkers()

    time.sleep(1)
    fifo_link = int(args.read_fifo)
    df = DataFrame(args.etroc)
    if fifo_link>=0:
        fifo = FIFO(rb_0, elink=fifo_link, ETROC=args.etroc)
        fifo.set_trigger(
            df.get_trigger_words(),
            df.get_trigger_masks(),
            )
        fifo.reset()
        try:
            hex_dump = fifo.giant_dump(300,255, align=(args.etroc=="ETROC1"))
        except:
            print ("Dispatch failed, trying again.")
            hex_dump = fifo.giant_dump(300,255, align=(args.etroc=="ETROC1"))
        print (hex_dump)
        fifo.dump_to_file(fifo.wipe(hex_dump, trigger_words=[]))  # use 5 columns --> better to read for our data format
