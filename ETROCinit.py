# Use rb_init() to initialize and get initialized RB

from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import header, make_version_header, download_address_table
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame

from tamalero.SCA import SCA_CONTROL

import time
import random
import sys
import os

def powerUpDAQ(rb_0):
    rb_0.DAQ_LPGBT.power_up_init()
    if rb_0.DAQ_LPGBT.ver == 0:
        rom = "LPGBT.RO.ROMREG"
        testval = 0xA5
    else:
        rom = "LPGBT.RO.ROM.ROMREG"
        testval = 0xA6
    if (rb_0.DAQ_LPGBT.rd_reg(rom) != testval):
       print ("No communication with DAQ LPGBT... trying to reset DAQ MGTs")
       rb_0.DAQ_LPGBT.reset_daq_mgts()
       rb_0.DAQ_LPGBT.power_up_init()
       time.sleep(0.01)
       #print(hex(rb_0.DAQ_LPGBT.rd_reg(rom)))
       if (rb_0.DAQ_LPGBT.rd_reg(rom) != testval):
           print ("Still no communication with DAQ LPGBT. Quitting.")
           sys.exit(0)
    #rb_0.TRIG_LPGBT.power_up_init()
    rb_0.VTRX.get_version()
    print ("VTRX status at power up:")
    _ = rb_0.VTRX.status()
    rb_0.get_trigger()
    if rb_0.trigger:
        print ("Enabling VTRX channel for trigger lpGBT")
        rb_0.VTRX.enable(ch=1)
        time.sleep(1)
        print ("Power up init sequence for: Trigger")
        rb_0.TRIG_LPGBT.power_up_init()
    #rb_0.DAQ_LPGBT.power_up_init_trigger()

def getFWver(kcu_adr):
    kcu = KCU(name="tmp_kcu",
            #ipb_path="chtcp-2.0://localhost:10203?target=%s:50001"%kcu_adr,
            ipb_path="ipbusudp-2.0://%s:50001"%kcu_adr,
            adr_table="address_table/generic/etl_test_fw.xml")
    return kcu.firmware_version(quiet=True)

def doAlignment(rb_0, alignment):
    if type(alignment) == str:
        from tamalero.utils import load_alignment_from_file
        alignment_file = load_alignment_from_file(alignment)
    else:
        alignment_file = None
    rb_0.configure(alignment=alignment_file, data_mode=data_mode, etroc=etroc_ver)
    # this is very slow, especially for the trigger lpGBT.

def checkKCU(kcu, data):
    kcu.write_node("LOOPBACK.LOOPBACK", data)
    if (data != kcu.read_node("LOOPBACK.LOOPBACK")):
        print("No communications with KCU105... quitting")
        sys.exit(0)

# =========================
# ===== initialize RB =====
# =========================

def rb_init(
        kcu_adr          = "192.168.0.10",
        power_up         = False,
        reconfigure      = False,
        force_no_trigger = False,
        etroc_ver        = "ETROC1",
        alignment        = False,
        ):

    header()

    data_mode = False
    if etroc_ver in ['ETROC1', 'ETROC2']: data_mode = True

    print ("Using KCU at address: %s"%kcu_adr)

    # Get the current firmware version number
    fw_version = getFWver(kcu_adr)

    if not os.path.isdir(f"address_table/v{fw_version}"):
        print ("Downloading latest firmware version address table.")
        download_address_table(fw_version)

    # initialize kcu
    kcu = KCU(name="my_device",
              #ipb_path="chtcp-2.0://localhost:10203?target=%s:50001"%kcu_adr,
              ipb_path="ipbusudp-2.0://%s:50001"%kcu_adr,
              adr_table=f"address_table/v{fw_version}/etl_test_fw.xml")

    # initialize RB
    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=(not force_no_trigger), kcu=kcu))

    kcu.firmware_version()

    kcu.write_node("READOUT_BOARD_%s.LPGBT.FEC_ERR_RESET" % 0, 0x1)
    kcu.status()

    # check communication with KCU
    checkKCU(kcu, 0xabcd1234)

    if power_up:
        print ("Power up init sequence for: DAQ")
        powerUpDAQ(rb_0)

    if not hasattr(rb_0, "TRIG_LPGBT"):
        rb_0.get_trigger()

    if power_up or reconfigure:
        if alignment:
            doAlignment(rb_0, alignment)
        if rb_0.trigger:
            time.sleep(1.0)
            rb_0.DAQ_LPGBT.reset_trigger_mgts()
            kcu.write_node("READOUT_BOARD_%s.LPGBT.FEC_ERR_RESET" % 0, 0x1)
        time.sleep(1.0)

    res = rb_0.DAQ_LPGBT.get_board_id()
    res['trigger'] = 'yes' if rb_0.trigger else 'no'
    make_version_header(res)

   # for ch in [2,3]:
   #     print (f"Disabling VTRx+ channel {ch}")
   #     rb_0.VTRX.disable(channel=ch)

    #rb_0.reset_FEC_error_count()
    #while not rb_0.DAQ_LPGBT.link_status():
    #    print ("DAQ link is not stable. Resetting.")
    #    rb_0.reset_link(trigger=False)
    #if rb_0.trigger:
    #    while not rb_0.TRIG_LPGBT.link_status(verbose=True):
    #        print ("Trigger link is not stable. Resetting.")
    #        rb_0.reset_link(trigger=True)

    rb_0.status()
    _ = rb_0.VTRX.status()

    rb_0.DAQ_LPGBT.set_dac(1.0)  # set the DAC / Vref to 1.0V.

    return rb_0
