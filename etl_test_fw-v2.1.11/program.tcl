set basename [file rootname [lindex [glob *.bit] 0]]
set bitfile ${basename}.bit
set binfile ${basename}.bin
set ltxfile ${basename}.ltx
set part     xcku040

proc program_flash {binfile devicename flash} {

    puts " > Programming Flash"

    set device [lindex [get_hw_devices $devicename] 0]
    set program_hw_cfgmem [get_property PROGRAM.HW_CFGMEM $device]

    create_hw_cfgmem -hw_device $device [lindex [get_cfgmem_parts $flash] 0]

    set_property PROGRAM.BLANK_CHECK 0 [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.ERASE       1 [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.CFG_PROGRAM 1 [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.VERIFY      1 [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.CHECKSUM    0 [get_property PROGRAM.HW_CFGMEM $device]

    refresh_hw_device -quiet $device

    set_property PROGRAM.ADDRESS_RANGE          {use_file}  [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.FILES           [list "$binfile" ] [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.PRM_FILE               {}          [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.UNUSED_PIN_TERMINATION {pull-none} [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.BLANK_CHECK            0           [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.ERASE                  1           [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.CFG_PROGRAM            1           [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.VERIFY                 1           [get_property PROGRAM.HW_CFGMEM $device]
    set_property PROGRAM.CHECKSUM               0           [get_property PROGRAM.HW_CFGMEM $device]

    create_hw_bitstream -hw_device $device [get_property PROGRAM.HW_CFGMEM_BITFILE $device];
    program_hw_devices $device;
    refresh_hw_device -quiet $device;
    program_hw_cfgmem -hw_cfgmem [get_property PROGRAM.HW_CFGMEM $device]
}

open_hw_manager -quiet
connect_hw_server -quiet -url localhost:3121
refresh_hw_server -quiet

set known_boards [dict create \
    210308AB9AC5 "BU Right 192.168.0.11" \
    210308AB9ACD "BU Left 192.168.0.10" \
    210308B0B4F5 "CI 192.168.0.12"]

set targets [get_hw_targets -quiet]
set num_targets [llength $targets]

if {$num_targets == 0} {
    puts "ERROR: No hardware targets found"
    exit 0
} else {
    # make a dictionary of the device names (e.g. xc7v...)
    set devices [dict create]
    foreach target $targets {
        close_hw_target -quiet
        open_hw_target -quiet $target
        set device [get_hw_devices -quiet ${part}*]
        if {[llength $device] > 0} {
            puts "Device=$device"
            dict set devices $target $device
            close_hw_target -quiet
        }
    }
}

set targets [dict keys $devices]

# allow specifying the target from the command line
if {[llength $argv] > 0} {
    set clisel [lindex $argv 0]
    set targetsel ""
    if {[dict exists $known_boards $clisel]} {
        puts "Target $clisel"
        foreach target $targets {
            if {[string first  "Digilent/$clisel" $target] != -1} {
                puts $target
                lappend targetsel $target
            }
        }
    }
    set targets $targetsel
} else {
    if {[llength $targets] == 1} {
        set target $targets
        puts "Target $target [dict get $devices $target] found, press y key to continue."
        gets stdin select
        if {[string equal $select "y"]} {
            set targets $target
        } else {
            puts "No target selected"
            exit 0
        }
    } elseif {[llength $targets] > 1} {
        puts "Multiple hardware targets found"
        for {set i 0} {$i < [llength $targets]} {incr i} {
            set target [lindex $targets $i]
            puts "  > $i $target"
            puts "      [dict get $devices $target]"

            set dsn [lindex [split "$target" "/"] end]
            if {[dict exists $known_boards $dsn]} {
                puts "      ([dict get $known_boards $dsn])"

            }
        }

        puts "  > \"all\" to program all"
        puts "  > anything else to quit"

        puts "Please select a target:"

        gets stdin select

        puts "$select selected"

        if {[string equal $select "all"]} {
            set targets $targets
        } elseif {![string is integer $select] || $select > $num_targets-1} {
            puts "Invalid target selected"
            exit 0
        } else {
            set targets [lindex $targets $select]
            puts " > selected $targets"
        }
    }
}

foreach target $targets {
    puts " > Programming $target"
    get_hw_targets
    open_hw_target $target
    set device [dict get $devices $target]
    if {[llength $device] > 0} {

        set programmed "False"

        if {[string equal $device $device]} {
            if {[llength $argv] == 2 && [string equal [lindex $argv 1] "noflash"]} {
                puts " > Skipping flash programming..."
            } else {
                puts "do you want to program the Flash? y/n"
                gets stdin select
                if {[string equal $select "y"]} {
                    program_flash $binfile $device "mt25qu256-spi-x1_x2_x4"
                    boot_hw_device  [lindex [get_hw_devices $device] 0]
                    set programmed "True"
                }
            }
        }

        if {[string equal $programmed "True"] == 0} {
            puts " > Programming FPGA"
            current_hw_device [get_hw_devices $device]
            refresh_hw_device -update_hw_probes false $device
            set_property PROGRAM.FILE $bitfile $device
            set_property PROBES.FILE $ltxfile $device
            set_property FULL_PROBES.FILE $ltxfile $device
            program_hw_devices $device
            close_hw_target
        }
    }
}
