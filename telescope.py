#!/usr/bin/env python3
'''
RB0 and RB1 connected to KCU 192.168.0.10
on PSU 192.168.2.1 ch1 and ch2
'''
import time
from emoji import emojize

from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import get_kcu
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame

from cocina.PowerSupply import PowerSupply

layers = [
    [
        [12],
        [],
        [11],  # dead??
    ],
    [
        [],
        #[11],
        [25],
        []
    ]
]

if __name__ == '__main__':
    shut_down = False

    print(emojize(':atom_symbol:'), " Telescope code draft")

    print(emojize(':battery:'), " Power Supply")
    psu1 = PowerSupply(ip='192.168.2.1', name='PS1')
    psu1.power_up('ch1')
    psu1.power_up('ch2')
    psu2 = PowerSupply(ip='192.168.2.2', name='PS2')
    psu2.power_up('ch1')
    time.sleep(1)
    print(emojize(":check_mark_button:"), " Ready")

    print("Getting the KCU")
    kcu = get_kcu('192.168.0.10', control_hub=True, verbose=True)

    print("Setting up Readout Boards")
    rb_0 = ReadoutBoard(0, kcu=kcu, config='modulev0b', verbose=False)
    rb_1 = ReadoutBoard(1, kcu=kcu, config='modulev0b', verbose=False)
    #rb_2 = ReadoutBoard(2, kcu=kcu, config='modulev0b', verbose=False)  # links not getting ready yet
    rb_2 = ReadoutBoard(2, kcu=kcu, config='modulev0b', verbose=False)

    print("Connecting Modules")
    rb_0.connect_modules()
    rb_1.connect_modules()
    rb_2.connect_modules()

    print("Showing status")
    rb_0.modules[0].show_status()
    #rb_0.modules[2].show_status()
    rb_1.modules[1].show_status()

    rb_0.modules[0].ETROCs[0].test_config(occupancy=127)
    #rb_0.modules[2].ETROCs[0].test_config(occupancy=127)
    rb_1.modules[1].ETROCs[0].test_config(occupancy=127)

    fifo_0 = FIFO(rb_0)
    fifo_1 = FIFO(rb_1)
    df = DataFrame("ETROC2")

    # doesn't matter which FIFO to choose, the L1A is universial
    print(emojize(':factory:'), " Producing data")
    fifo_0.send_l1a(2)

    print(emojize(':closed_mailbox_with_raised_flag:'), " Data in FIFO 0:")
    for x in fifo_0.pretty_read(df):
        print(x)

    print(emojize(':closed_mailbox_with_raised_flag:'), " Data in FIFO 1:")
    for x in fifo_1.pretty_read(df):
        print(x)

    if shut_down:
        psu1.power_down('ch1')
        psu1.power_down('ch2')
        psu2.power_down('ch1')
