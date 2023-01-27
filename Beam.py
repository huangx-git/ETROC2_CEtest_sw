#!/usr/bin/env python3
import uhal
import os
import time
import struct
import datetime

class Beam():
    def __init__(self, rb):
        try:
            self.rb  = rb
            self.kcu = self.rb.kcu
        except:
            print("Unable to connect to KCU.")
        self.ON = 4
        self.OFF = 56
        self.cycles = 0

    def generate_beam(self, l1a_rate, nmin, verbose=False):
        """
        Simulates Fermilab's test beam (4s ON, 56s OFF), sending L1A signals at l1a_rate MHz [default = 1] for nmin minutes [default = 1]
        """

        self.SIM = True

        if verbose: print("Preparing beam...")

        uhal.disableLogging()

        self.l1a_rate = l1a_rate
        self.nmin = nmin

        self.trigger_rate = self.l1a_rate * 1000000 / 25E-9 / (0xffffffff) * 10000

        ON_TIME = self.ON
        OFF_TIME = self.OFF

        START = time.time()

        for minute in range(self.nmin):

            if verbose: print("### Beam ON ###")

            self.kcu.write_node("SYSTEM.L1A_RATE", int(self.trigger_rate))

            time.sleep(1)

            start_ON = time.time()

            time.sleep(ON_TIME)
            
            time_diff_ON = time.time() - start_ON

            l1a_rate_cnt_ON = self.kcu.read_node("SYSTEM.L1A_RATE_CNT")

            if verbose:
                print("Shutting off beam...") 
                print("\tON time  = {:.2f} s".format(time_diff_ON))
                print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_ON.value()/1000000.0))

                print("### Beam OFF ###")

            self.kcu.write_node("SYSTEM.L1A_RATE", 0)

            time.sleep(1)

            start_OFF = time.time()

            time.sleep(OFF_TIME)

            time_diff_OFF = time.time() - start_OFF

            l1a_rate_cnt_OFF = self.kcu.read_node("SYSTEM.L1A_RATE_CNT")

            self.cycles += 1

            if verbose:
                print("{} minutes completed".format(minute+1))
                print("\tOFF time = {:.2f} s".format(time_diff_OFF))
                print("\tL1A rate = {:.2f} MHz".format(l1a_rate_cnt_OFF.value()/1000000.0))

        total_time = round(time.time() - START)
        total_time = str(datetime.timedelta(seconds=total_time-2))
        if verbose: print("Test beam simulation completed; it took {}.".format(total_time))
        self.SIM = False

    def read_beam(self, block=255, verbose=False, zipped=True):
        if verbose: start = time.time()
        if zipped:
            from zipfile import ZipFile
            zip_time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S") 
            files = []
            zip_file = f"output/read_beam_{zip_time_stamp}.zip"
        while self.SIM:
            data = []
            while self.kcu.read_node("SYSTEM.L1A_RATE_CNT") != 0:
                try:
                    # Check FIFO occupancy
                    occupancy = self.kcu.read_node("READOUT_BOARD_0.RX_FIFO_OCCUPANCY")
                    num_blocks_to_read = occupancy.value() // block

                    # Read data from FIFO
                    if (num_blocks_to_read):
                        reads = num_blocks_to_read * [self.kcu.hw.getNode("DAQ_RB0").readBlock(block)]
                        self.kcu.dispatch()
                        for read in reads:
                            data += read.value()
                except uhal._core.exception:
                    print("uhal UDP error in daq")

            if data:
                time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                with open(f"output/read_beam_{time_stamp}.dat", mode="wb") as f:
                    f.write(struct.pack('<{}I'.format(len(data)), *data))
                    files.append(f"output/read_beam_{time_stamp}.dat")
                    if verbose:
                        time_diff = round(time.time() - start)
                        time_diff = str(datetime.timedelta(seconds=time_diff))
                        print(f"Writing after {time_diff}")

        if zipped:
            with ZipFile(zip_file, 'w') as zfile:
                for f in files:
                    zfile.write(f)
                    os.remove(f)

    def monitoring_beam(self, on=True):
        from rich.table import Table
        from rich.live import Live
        from rich.layout import Layout
        from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn, BarColumn, TaskProgressColumn
        from rich.panel import Panel
        from rich.console import Console

        from beam_utils import generate_table, generate_header, generate_static

        from collections import deque
        import os

        console = Console()

        layout = Layout(name="root")

        layout.split_column(
            Layout(name="header", size=12),
            Layout(name="main", ratio=1)
        )

        layout["main"].split_row(
            Layout(name="dynamic", ratio=2),
            Layout(name="parameters", ratio=1),
        )
        layout["parameters"].split_column(
            Layout(name="static"),
            Layout(name="progress", size=5)
       )

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        )
        total = self.nmin * 60
        sim_task = progress.add_task("[bold green]Beam Simulation", total=total)
        
        render_map = layout["dynamic"].render(console, console.options)
        n_rows = render_map[layout["dynamic"]].region.height

        width, height = os.get_terminal_size()
        table_height = int((height - 12) * 2 / 3)
        rows = deque(maxlen=table_height)

        with Live(layout, vertical_overflow="crop", console=console) as live:    
            while self.SIM:
                l1a_rate_cnt = self.kcu.read_node("SYSTEM.L1A_RATE_CNT").value()/1000000.0
                time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cycles = self.cycles
                occupancy = self.kcu.read_node("READOUT_BOARD_0.RX_FIFO_OCCUPANCY")
                temps = self.rb.read_temp()
                rows.append((f"[bold red]{time_stamp}", f"{cycles}", f"{l1a_rate_cnt}", f"{occupancy}", f"{temps['t1']:.2f}", f"{temps['t2']:.2f}", f"{temps['t_SCA']:.2f}"))

                #layout["dynamic"].update(generate_table(rows, n_rows, layout["dynamic"], console))
                layout["dynamic"].update(generate_table(rows))
                layout["progress"].update(Panel(progress, expand=True))
                layout["header"].update(generate_header())
                layout["static"].update(generate_static())
                #live.update(generate_table(), refresh=True)
                progress.update(sim_task, advance=1)
                time.sleep(1) 
