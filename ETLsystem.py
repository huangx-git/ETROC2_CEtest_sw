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

def get_fw_ver(kcu_adr):
    kcu = KCU(name="tmp_kcu",
            ipb_path="ipbusudp-2.0://%s:50001"%kcu_adr,
            adr_table="address_table/generic/etl_test_fw.xml")
    return kcu.firmware_version(quiet=True)

def initialize(
        kcu_adr          = "192.168.0.10",
        force_no_trigger = "False",
        etroc_ver        = "ETROC1",
        load_alignment   = None,
        ):

    header()

    print ("Using KCU at address: %s"%kcu_adr)

    # Get the current firmware version number
    fw_version = get_fw_ver(kcu_adr)

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

