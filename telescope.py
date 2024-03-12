#!/usr/bin/env python3
'''
RB0 and RB1 connected to KCU 192.168.0.10
on PSU 192.168.2.1 ch1 and ch2
'''
import time
import copy
from emoji import emojize

from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import get_kcu
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame

from cocina.PowerSupply import PowerSupply

'''
Configuration of the telescope
'''
layers = [
    [
        [40],
        [],
        [],
    ],
#    [
#        [],  # 36
#        [],
#        [],
#    ],
#    [
#        [],  # 38
#        [],
#        []
#    ],
#    [
#        [39],
#        [],
#        []
#    ],
]

if __name__ == '__main__':


    import argparse
    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default='192.168.0.10', help="IP Address of KCU105 board")
    argParser.add_argument('--configuration', action='store', default='modulev0b', choices=['modulev0', 'modulev0b'], help="Board configuration to be loaded")
    argParser.add_argument('--host', action='store', default='localhost', help="Hostname for control hub")
    argParser.add_argument('--enable_power_board', action='store_true', help="Enable Power Board (all modules). Jumpers must still be set as well.")
    argParser.add_argument('--test_config', action='store_true', help="Use a test configuration.")
    argParser.add_argument('--power_up', action='store_true', help="Turn power on (BU setup only)")
    argParser.add_argument('--power_down', action='store_true', help="Turn power off (BU setup only)")
    argParser.add_argument('--subset', action='store_true', help="Use subset of pixels for tests")
    argParser.add_argument('--offset', action='store', default='auto', help="The offset from the baseline")
    args = argParser.parse_args()


    shut_down = False
    connect_modules = True

    print(emojize(':atom_symbol:'), " Telescope code draft")

    if args.power_up:
        print(emojize(':battery:'), " Power Supply")
        psu1 = PowerSupply(ip='192.168.2.1', name='PS1')
        psu1.power_up('ch1')
        psu1.power_up('ch2')
        #psu2 = PowerSupply(ip='192.168.2.2', name='PS2')
        #psu2.power_up('ch1')
        time.sleep(1)
    print(emojize(":check_mark_button:"), " Ready")

    print("Getting the KCU")
    kcu = get_kcu(args.kcu, control_hub=True, verbose=True)


    print("Configuring Readout Boards")
    rbs = {}
    for i, layer in enumerate(layers):
        print(i)
        rbs[i] = ReadoutBoard(rb=i, trigger=True, kcu=kcu, config=args.configuration, verbose=False)


    #print("Scanning Readout Boards")
    #irbs = []
    #for i in range(5):
    #    # we can at most connect 5 RBs
    #    try:
    #        rb_tmp = ReadoutBoard(rb=i, trigger=False, kcu=kcu, config=args.configuration, verbose=False)
    #        #rbs.append(rb_tmp)
    #        #rbs.append(ReadoutBoard(rb=i, trigger=True, kcu=kcu, config=args.configuration, verbose=False))
    #        print(f"Added RB #{i}")
    #        irbs.append(i)
    #    except:
    #        print(f"Could not add RB#{i}")
    #        #raise

    #print("Configuring Readout Boards")
    #rbs = {}
    #for i in irbs:
    #    rbs[i] = ReadoutBoard(rb=i, trigger=True, kcu=kcu, config=args.configuration, verbose=False)


    if connect_modules:

        print("Connecting Modules")
        for rb in rbs:
            moduleids = [x[0] if len(x)>0 else 0 for x in layers[rb]]
            print(moduleids)
            rbs[rb].connect_modules(moduleids=moduleids)
        #    rb.rerun_bitslip()

            for mod in rbs[rb].modules:
                mod.show_status()

        print("Configuring ETROCs")
        for rb in rbs:
            for mod in rbs[rb].modules:
                if mod.connected:
                    if args.test_config:
                        mod.ETROCs[0].test_config(occupancy=10)
                    else:
                        if args.subset:
                            test_pixels = [
                                #(0,0),
                                (1,1),
                                (7,7),
                                (7,8),
                                (8,8),
                                (8,7),
                                (0,15),
                                (15,0),
                                (15,15),
                            ]
                        else:
                            test_pixels = False
                        if args.offset == 'auto':
                            offset = args.offset
                        else:
                            offset = int(args.offset)
                        mod.ETROCs[0].physics_config(offset=offset, L1Adelay=15, subset=test_pixels)
                    mod.ETROCs[0].reset()

        fifo_0 = FIFO(rbs[0])
        #fifo_1 = FIFO(rbs[1])
        df = DataFrame("ETROC2")

        fifo_0.send_l1a(1)
        fifo_0.reset()
        #fifo_1.reset()

        # doesn't matter which FIFO to choose, the L1A is universial
        print(emojize(':factory:'), " Producing some test data")
        fifo_0.send_l1a(10)

        print(emojize(':closed_mailbox_with_raised_flag:'), " Data in FIFO 0:")
        for x in fifo_0.pretty_read(df):
            #if x[0] == 'data': print ('!!!!!!!!!!', x)
            print(x)

        #print(emojize(':closed_mailbox_with_raised_flag:'), " Data in FIFO 1:")
        #for x in fifo_1.pretty_read(df):
        #    #if x[0] == 'data': print ('!!!!!!!!!!', x)
        #    print(x)

        # This script was verified to work with noise at the BU test stands
        # and it actually sees noise on the wirebonded pixels, as expected

    run_timing_scan = False
    #rbs[0].modules[0].ETROCs[0].disable_data_readout(broadcast=True)
    #rbs[0].modules[0].ETROCs[0].enable_data_readout(row=8, col=8, broadcast=False)
    #rbs[0].modules[0].ETROCs[0].wr_reg("DAC", 302, row=8, col=8, broadcast=False)
    if run_timing_scan:
        rbs[0].modules[0].ETROCs[0].disable_data_readout(row=2, col=10, broadcast=False)
        rbs[0].modules[0].ETROCs[0].disable_data_readout(row=1, col=15, broadcast=False)
        rbs[0].modules[0].ETROCs[0].disable_data_readout(row=7, col=15, broadcast=False)
        rbs[0].enable_external_trigger()
        for i in range(40):
            rbs[0].modules[0].ETROCs[0].wr_reg("L1Adelay", i, broadcast=True)  # broadcast was missing before.
            rbs[0].reset_data_error_count()
            kcu.write_node(f"READOUT_BOARD_0.EVENT_CNT_RESET", 0x1)
            fifo_0.reset()
            while kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()<300:
                time.sleep(0.01)
            #time.sleep(10)
            #fifo_0.send_l1a(100)
            #time.sleep(0.1)
            #res = fifo_0.pretty_read(df)
            data_count = rbs[0].read_data_count(elink=0, slave=False)
            trigger_count = kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()
            print(i, data_count, trigger_count)
            #start_time = time.time()
            #while time.time() - start_time < 10:

        
    if args.power_down:
        psu1.power_down('ch1')
        psu1.power_down('ch2')
        #psu2.power_down('ch1')
