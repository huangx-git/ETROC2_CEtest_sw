from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.console import Console

from collections import deque
import os

#def generate_table(rows, n_rows, layout, console) -> Table:
#
#    table = Table(show_header=True, header_style="bold magenta", expand=True)
#    table.add_column("Time")
#    table.add_column("Beam Cycles")
#    table.add_column("L1A Rate Count [MHz]", justify="right")
#    table.add_column("FIFO Occupancy", justify="right")
#    table.add_column("RB RT1 Temperature [°C]", justify="right")
#    table.add_column("RB RT2 Temperature [°C]", justify="right")
#    table.add_column("RB SCA Temperature [°C]", justify="right")
#
#    rows = list(rows)
#
#    while n_rows >= 0:
#        table = Table(show_header=True, header_style="bold magenta")
#        table.add_column("Time")
#        table.add_column("Beam Cycles")
#        table.add_column("L1A Rate Count [MHz]", justify="right")
#        table.add_column("FIFO Occupancy", justify="right")
#        table.add_column("RB RT1 Temperature [°C]", justify="right")
#        table.add_column("RB RT2 Temperature [°C]", justify="right")
#        table.add_column("RB SCA Temperature [°C]", justify="right")
#
#        for row in rows[-n_rows:]:
#            table.add_row(*row)
#
#        layout.update(table)
#
#        render_map = layout.render(console, console.options)
#
#        if len(render_map[layout].render[-1]) > 2:
#            # The table is overflowing
#            n_rows -= 1
#        else:
#            break
#
#    return table
#
def generate_table(rows):
    layout = Layout()
    console = Console()

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Time")
    table.add_column("Beam Cycles")
    table.add_column("L1A Rate Count [MHz]", justify="right")
    table.add_column("FIFO Occupancy", justify="right")
    table.add_column("RB RT1 Temperature [°C]", justify="right")
    table.add_column("RB RT2 Temperature [°C]", justify="right")
    table.add_column("RB SCA Temperature [°C]", justify="right")

    rows = list(rows)

    # This would also get the height:
    render_map = layout.render(console, console.options)
    n_rows = render_map[layout].region.height

    while n_rows >= 0:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time")
        table.add_column("Beam Cycles")
        table.add_column("L1A Rate Count [MHz]", justify="right")
        table.add_column("FIFO Occupancy", justify="right")
        table.add_column("RB RT1 Temperature [°C]", justify="right")
        table.add_column("RB RT2 Temperature [°C]", justify="right")
        table.add_column("RB SCA Temperature [°C]", justify="right")

        for row in rows[-n_rows:]:
            table.add_row(*row)

        layout.update(table)

        render_map = layout.render(console, console.options)

        if len(render_map[layout].render[-1]) > 2:
            # The table is overflowing
            n_rows -= 1
        else:
            break

    return table

def generate_header() -> Panel:
    tamalero_header = """
    ████████╗ █████╗ ███╗   ███╗ █████╗ ██╗     ███████╗███████╗\n\
    ╚══██╔══╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝██╔════╝\n\
       ██║   ███████║██╔████╔██║███████║██║     █████╗  ███████╗\n\
       ██║   ██╔══██║██║╚██╔╝██║██╔══██║██║     ██╔══╝  ╚════██║\n\
       ██║   ██║  ██║██║ ╚═╝ ██║██║  ██║███████╗███████╗███████║\n\
       ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝\n\
    """.splitlines()

    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    for i, line in enumerate(tamalero_header):
        grid.add_row(tamalero_header[i])
    #grid.add_row(tamalero_header[0])
    #grid.add_row(tamalero_header[1])
    #grid.add_row(tamalero_header[2])
    #grid.add_row(tamalero_header[3])
    #grid.add_row(tamalero_header[4])
    #grid.add_row(tamalero_header[5])
    grid.add_row("[underline italic]Fermilab Test Beam Simulation")

    return Panel(grid, style="magenta")

def generate_static() -> Panel:
    current_dir = os.getcwd()
    # output_dir = 

    grid = Table.grid(expand=True)
    grid.add_column(justify="right", ratio=1)
    grid.add_column(justify="left", ratio=2)
    grid.add_row("Current Directory:", current_dir)
    return Panel(grid)
