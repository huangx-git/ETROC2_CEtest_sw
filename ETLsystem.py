from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import header, make_version_header, download_address_table
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame
from tamalero.SCA import SCA_CONTROL
from tamalero.utils import get_temp

import time
import sys
import os

def initialize(
        kcu_adr          = "192.168.0.10",
        force_no_trigger = "False",
        etroc_ver        = "ETROC1",
        load_alignment   = None,
        read_fifo        = -1
        ):

    header()

    data_mode = False
    if etroc_ver in ['ETROC1', 'ETROC2']: data_mode = True

    print ("Using KCU at address: %s"%kcu_adr)

    # Get the current firmware version number
    kcu_tmp = KCU(name="tmp_kcu",
                  ipb_path="ipbusudp-2.0://%s:50001"%kcu_adr,
                  adr_table="address_table/generic/etl_test_fw.xml")
    fw_version = kcu_tmp.firmware_version(quiet=True)

    if not os.path.isdir(f"address_table/v{fw_version}"):
        print ("Downloading latest firmware version address table.")
        download_address_table(fw_version)

    kcu = KCU(name="my_device",
              ipb_path="ipbusudp-2.0://%s:50001"%kcu_adr,
              adr_table=f"address_table/v{fw_version}/etl_test_fw.xml")

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=(not force_no_trigger)))

    kcu.firmware_version()

    kcu.write_node("READOUT_BOARD_%s.LPGBT.FEC_ERR_RESET" % 0, 0x1)
    kcu.status()

    data = 0xabcd1234
    kcu.write_node("LOOPBACK.LOOPBACK", data)
    if (data != kcu.read_node("LOOPBACK.LOOPBACK")):
        print("No communications with KCU105... quitting")
        sys.exit(0)

    print ("Power up init sequence for: DAQ")
    rb_0.DAQ_LPGBT.power_up_init()
    if (rb_0.DAQ_LPGBT.rd_adr(0x1c5) != 0xa5):
        print ("No communication with DAQ LPGBT... trying to reset DAQ MGTs")
        rb_0.DAQ_LPGBT.reset_daq_mgts()
        rb_0.DAQ_LPGBT.power_up_init()
        time.sleep(0.01)
        #print(hex(rb_0.DAQ_LPGBT.rd_adr(0x1c5)))
        if (rb_0.DAQ_LPGBT.rd_adr(0x1c5) != 0xa5):
            print ("Still no communication with DAQ LPGBT. Quitting.")
            sys.exit(0)
    #rb_0.TRIG_LPGBT.power_up_init()
    rb_0.get_trigger()
    if rb_0.trigger:
        print ("Power up init sequence for: Trigger")
        rb_0.TRIG_LPGBT.power_up_init()
    #rb_0.DAQ_LPGBT.power_up_init_trigger()

    if not hasattr(rb_0, "TRIG_LPGBT"):
        rb_0.get_trigger()

    if load_alignment is not None:
        from tamalero.utils import load_alignment_from_file
        alignment = load_alignment_from_file(load_alignment)
    else:
        alignment = None
    rb_0.configure(alignment=alignment, data_mode=data_mode, etroc=etroc_ver)
    # this is very slow, especially for the trigger lpGBT.
    if rb_0.trigger:
        time.sleep(1.0)
        rb_0.DAQ_LPGBT.reset_trigger_mgts()
        kcu.write_node("READOUT_BOARD_%s.LPGBT.FEC_ERR_RESET" % 0, 0x1)
        time.sleep(1.0)

    res = rb_0.DAQ_LPGBT.get_board_id()
    res['trigger'] = 'yes' if rb_0.trigger else 'no'
    make_version_header(res)

    for ch in [2,3]:
        print (f"Disabling VTRx+ channel {ch}")
        rb_0.VTRX.disable(channel=ch)

    rb_0.reset_FEC_error_count()
    while not rb_0.DAQ_LPGBT.link_status():
        print ("DAQ link is not stable. Resetting.")
        rb_0.reset_link(trigger=False)
    if rb_0.trigger:
        while not rb_0.TRIG_LPGBT.link_status():
            print ("Trigger link is not stable. Resetting.")
            rb_0.reset_link(trigger=True)

    rb_0.status()

    _ = rb_0.VTRX.status()

    rb_0.DAQ_LPGBT.set_dac(1.0)  # set the DAC / Vref to 1.0V.

    print("\n\nReading GBT-SCA ADC values:")
    rb_0.SCA.read_adcs()

    print("\n\nReading DAQ lpGBT ADC values:")
    rb_0.DAQ_LPGBT.read_adcs()

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


    if data_mode:
        time.sleep(1)
        fifo_link = int(read_fifo)
        df = DataFrame(etroc_ver)
        if fifo_link>=0:
            fifo = FIFO(rb_0, elink=fifo_link, ETROC=etroc_ver)
            fifo.set_trigger(
                df.get_trigger_words(),
                df.get_trigger_masks(),
                )
            fifo.reset()
            try:
                hex_dump = fifo.giant_dump(300,255, align=(etroc_ver=="ETROC1"))
            except:
                print ("Dispatch failed, trying again.")
                hex_dump = fifo.giant_dump(300,255, align=(etroc_ver=="ETROC1"))
            print (hex_dump)
            fifo.dump_to_file(fifo.wipe(hex_dump, trigger_words=[]))
            # use 5 columns --> better to read for our data format
