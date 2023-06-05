from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import header, make_version_header, get_kcu, check_repo_status
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame
from tamalero.ETROC import ETROC
from tamalero.Module import Module

from tamalero.SCA import SCA_CONTROL

import time
import random
import sys
import os
import uhal
from emoji import emojize
from flask import Flask

def create_app(rb, modules=[]):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    @app.route('/rb_temp')
    def temperatures():
        return rb.read_temp()

    @app.route('/module_links')
    def get_ink_status():
        link_status = {}
        for i, m in enumerate(modules):
            link_status[i] = m.get_locked_links()
        return link_status

    return app

if __name__ == '__main__':


    import argparse

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--verbose', action='store_true', default=False, help="Verbose power up sequence")
    argParser.add_argument('--power_up', action='store_true', default=False, help="Do lpGBT power up init?")
    argParser.add_argument('--reconfigure', action='store_true', default=False, help="Configure the RB electronics: SCA and lpGBT?")
    argParser.add_argument('--adcs', action='store_true', default=False, help="Read ADCs?")
    argParser.add_argument('--i2c_temp', action='store_true', default=False, help="Do temp monitoring on I2C from lpGBT?")
    argParser.add_argument('--i2c_sca', action='store_true', default=False, help="I2C tests on SCA?")
    argParser.add_argument('--run_pattern_checker', action='store_true', default=False, help="Read pattern checker?")
    argParser.add_argument('--reset_pattern_checker', action='store', choices=[None, 'prbs', 'upcnt'], default=None, help="Reset pattern checker?")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--force_no_trigger', action='store_true', help="Never initialize the trigger lpGBT.")
    argParser.add_argument('--allow_bad_links', action='store_true', help="Select to allow bad link initialization.")
    argParser.add_argument('--read_fifo', action='store', default=-1, help='Read 3000 words from link N')
    argParser.add_argument('--alignment', action='store', nargs='?', default=False, const=True, help='Load/scan alignment? If load, pass in file path')
    argParser.add_argument('--etroc', action='store', default="ETROC2", help='Specify ETROC version.')
    argParser.add_argument('--eyescan', action='store_true', default=False, help="Run eyescan?")
    argParser.add_argument('--recal_lpgbt', action='store_true', default=False, help="Recalibrate ADC in LPGBT? (instead of using saved values)")
    argParser.add_argument('--control_hub', action='store_true', default=False, help="Use control hub for communication?")
    argParser.add_argument('--host', action='store', default='localhost', help="Specify host for control hub")
    argParser.add_argument('--configuration', action='store', default='default', choices=['default', 'emulator', 'modulev0'], help="Specify a configuration of the RB, e.g. emulator or modulev0")
    argParser.add_argument('--devel', action='store_true', default=False, help="Don't check repo status (not recommended)")
    argParser.add_argument('--monitor', action='store_true', default=False, help="Start up montoring threads in the background")
    argParser.add_argument('--strict', action='store_true', default=False, help="Enforce strict limits on ADC reads for SCA and LPGBT")
    argParser.add_argument('--server', action='store_true', default=False, help="Start server")
    args = argParser.parse_args()


    verbose = args.verbose
    data_mode = args.etroc in ['ETROC1', 'ETROC2']

    #-------------------------------------------------------------------------------
    # Try to Connect to the KCU105
    #-------------------------------------------------------------------------------

    print ("Using KCU at address: %s"%args.kcu)

    kcu = None
    rb_0 = None

    # write to the loopback node of the KCU105 to check ethernet communication
    kcu = get_kcu(args.kcu, control_hub=args.control_hub, host=args.host, verbose=args.verbose)
    if (kcu == 0):
        # if not basic connection was established the get_kcu function returns 0
        # this would cause the RB init to fail.
        sys.exit(1)


    rb_0 = ReadoutBoard(0, trigger=(not args.force_no_trigger), kcu=kcu, config=args.configuration)
    data = 0xabcd1234
    kcu.write_node("LOOPBACK.LOOPBACK", data)
    if (data != kcu.read_node("LOOPBACK.LOOPBACK")):
        print("No communications with KCU105... quitting")
        sys.exit(1)

    is_configured = rb_0.DAQ_LPGBT.is_configured()
    header(configured=is_configured)

    if args.recal_lpgbt:
        rb_0.DAQ_LPGBT.calibrate_adc(recalibrate=True)
        if rb_0.trigger:
            rb_0.TRIG_LPGBT.calibrate_adc(recalibrate=True)

    if not args.devel:
        check_repo_status(kcu_version=kcu.get_firmware_version(verbose=True))

    #-------------------------------------------------------------------------------
    # Power up
    #-------------------------------------------------------------------------------

    if args.power_up:

        print("Power up init sequence for: DAQ")

        #rb_0.DAQ_LPGBT.power_up_init()

        rb_0.VTRX.get_version()
        if (verbose):
            print ("VTRX status at power up:")
            _ = rb_0.VTRX.status()
            print (rb_0.VTRX.ver)

        rb_0.get_trigger()

        if rb_0.trigger:
            #print("Configuring Trigger lpGBT")
            print (" > Power up init sequence for: Trigger")
            rb_0.TRIG_LPGBT.power_up_init()
            print("Done Configuring Trigger lpGBT")
    else:
        rb_0.VTRX.get_version()


    if not hasattr(rb_0, "TRIG_LPGBT"):
        rb_0.get_trigger()

    if args.power_up or args.reconfigure:

        if args.alignment:
            if isinstance(args.alignment, str):
                print ("Loading uplink alignemnt from file:", args.alignment)
                from tamalero.utils import load_alignment_from_file
                alignment = load_alignment_from_file(args.alignment)
            else:
                alignment = None
        else:
            alignment = False

        #if rb_0.trigger:
        #    rb_0.TRIG_LPGBT.power_up_init()
        print("Configuring readout board")
        rb_0.configure(alignment=alignment, data_mode=data_mode, etroc=args.etroc, verbose=args.verbose)

    res = rb_0.DAQ_LPGBT.get_board_id()
    res['trigger'] = 'yes' if rb_0.trigger else 'no'

    if (verbose):
        make_version_header(res)

    if args.power_up or args.reconfigure:
        rb_0.reset_problematic_links(
            max_retries=10,
            allow_bad_links=args.allow_bad_links)
        if verbose:
            rb_0.status()

    if (verbose):
        kcu.status()

    rb_0.VTRX.get_version()
    if (verbose):
        _ = rb_0.VTRX.status()


    if args.power_up or args.reconfigure:
        print("Link inversions")
        rb_0.DAQ_LPGBT.invert_links()
        if rb_0.trigger:
            rb_0.TRIG_LPGBT.invert_links(trigger=rb_0.trigger)

    #-------------------------------------------------------------------------------
    # Module Status
    #-------------------------------------------------------------------------------

    modules = []
    if args.configuration == 'emulator':
        print("Configuring ETROCs")
        for i in range(res['n_module']):
            modules.append(Module(rb_0, i+1))

        print()
        print("Querying module status")
        for m in modules:
            #m.configure()
            m.show_status()

        # Monitoring threads
        if args.monitor:
            from tamalero.Monitoring import Monitoring, module_mon
            #mon1 = module_mon(modules[0])
            monitoring_threads = []
            for i in range(res['n_module']):
                if modules[i].ETROCs[0].connected:
                    monitoring_threads.append(module_mon(modules[i]))

    if args.server:
        app = create_app(rb_0, modules=modules)
        app.run()

    #-------------------------------------------------------------------------------
    # Read ADCs
    #-------------------------------------------------------------------------------

    if args.adcs:
        print("\n\nReading GBT-SCA ADC values:")
        rb_0.SCA.read_adcs(check=True, strict_limits=args.strict)

        print("\n\nReading DAQ lpGBT ADC values:")
        rb_0.DAQ_LPGBT.read_adcs(check=True, strict_limits=args.strict)

        # High level reading of temperatures
        temp = rb_0.read_temp(verbose=True)

    #-------------------------------------------------------------------------------
    # I2C Test
    #-------------------------------------------------------------------------------

    if args.i2c_temp:

        for i in range(100):
            print ( rb_0.DAQ_LPGBT.read_temp_i2c() )
            time.sleep(1)

    #-------------------------------------------------------------------------------
    # Read SCA
    #-------------------------------------------------------------------------------

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

    #-------------------------------------------------------------------------------
    # Pattern Checkers
    #-------------------------------------------------------------------------------

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

    #-------------------------------------------------------------------------------
    # Eyescan
    #-------------------------------------------------------------------------------

    if args.eyescan:
        rb_0.DAQ_LPGBT.eyescan()

    all_tests_passed = True  # FIXME this should be properly defined
    if all_tests_passed:
        rb_0.DAQ_LPGBT.set_configured()

    #-------------------------------------------------------------------------------
    # Success LEDs
    #-------------------------------------------------------------------------------
    if rb_0.DAQ_LPGBT.ver == 1:
        rb_0.DAQ_LPGBT.set_gpio("LED_1", 1) # Set LED1 after tamalero finishes succesfully
        t_end = time.time() + 10
        if args.power_up:
            print("RB configured successfully. Rhett is happy " + emojize(":dog_face:"))
            while time.time() < t_end:
                rb_0.DAQ_LPGBT.set_gpio("LED_RHETT", 1) # Let Rhett LED blink for 10s
                time.sleep(0.5)
                rb_0.DAQ_LPGBT.set_gpio("LED_RHETT", 0)
                time.sleep(0.5)
        rb_0.DAQ_LPGBT.set_gpio("LED_RHETT", 1)
