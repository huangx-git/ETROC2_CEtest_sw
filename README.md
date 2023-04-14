# Software for basic ETL RB, PB and module (system) tests: Tamalero

```
 ████████╗ █████╗ ███╗   ███╗ █████╗ ██╗     ███████╗███████╗
 ╚══██╔══╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝██╔════╝
    ██║   ███████║██╔████╔██║███████║██║     █████╗  ███████╗
    ██║   ██╔══██║██║╚██╔╝██║██╔══██║██║     ██╔══╝  ╚════██║
    ██║   ██║  ██║██║ ╚═╝ ██║██║  ██║███████╗███████╗███████║
    ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
```

## Software structure

```
── Control Board (KCU105)
   ├── Readout Board 0
   │   ├── LPGBT
   │   ├── SCA
   │   ├── Power Board Interface
   │   ├── Module 0
   │   │   ├── ETROC0
   │   │   ├── ETROC1
   │   │   ├── ETROC2
   │   │   └── ETROC3
   │   ├── Module 1
   │   ├── ...
   │   └── Module N
   ├── Readout Board 1
   ├── Readout Board 2
   ├── ...
   └── Readout Board 9
```


## Dependencies

Tested on python 3.8.10.
Install the software with all its dependencies except IPbus:

``` shell
git clone https://gitlab.cern.ch/cms-etl-electronics/module_test_sw.git
pip install --editable .
```

To install IPbus please see the [IPbus user guide](https://ipbus.web.cern.ch/doc/user/html/software/installation.html).

## Running the code

To properly set all paths run `source setup.sh`.

A minimal example of usage of this package is given in `test_tamalero.py`, which can be run as:
`ipython3 -i test_tamalero.py`

The code is organized similar to the physical objects.
The 0th readout board object can be initialized with
```
rb_0 = ReadoutBoard(0, trigger=False, flavor='small')
```
where `trigger=False` defines that we don't deal with the trigger lpGBT (not yet fully implemented).
The current RB prototype is of the small flavor (3 modules, 12 ETROCs). We anticipate implementing different flavors in the future.

To interact with `rb_0` we need to initialize a control board (KCU105)
```
kcu = KCU(name="my_device",
          ipb_path="chtcp-2.0://localhost:10203?target=192.168.0.11:50001",
          adr_table="module_test_fw/address_tables/etl_test_fw.xml",
	  dummy=False)
```
and connect it to the readout board
```
rb_0.connect_KCU(kcu)
```

**Note:** Control hub is now required for using the KCU, as shown in the default `ipb_path` of the KCU (i.e. `"chtcp-2.0://localhost:10203?target=192.168.0.11:50001"` instead of `"ipbusudp-2.0://192.168.0.11:50001"`). `tamalero` won't run otherwise.

We can then configure the RB and get a status of the lpGBT:
```
rb_0.configure()
rb_0.DAQ_LPGBT.status()
``` 

Now we're all set! Some high level functions are currently being implemented.
An example is the following:
```
rb_0.read_temp(verbose=1)
```
that reads the temperature of all the available sensors on the board. The output looks like this
```
V_ref is set to: 0.900 V

Temperature on RB RT1 is: 33.513 C
Temperature on RB RT2 is: 34.138 C
Temperature on RB SCA is: 32.668 C
```

One can interact with the lpGBT and SCA directly, either via `rb_0.DAQ_LPGBT` or `rb_0.SCA`.
The classes are defined in [here](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/tree/master/tamalero).

The current reading of the SCA ADCs can be obtained with
```
rb_0.SCA.read_adcs()
```
which reads all ADC lines that are connected, according to the mapping given in [configs/SCA_mapping.yaml](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/blob/master/configs/SCA_mapping.yaml) or [configs/SCA_mapping_v2.yaml](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/blob/master/configs/SCA_mapping_v2.yaml) depending on the readout board version.
An example is given here:
```
adc:
    1V2_mon0:
        pin: 0x01
        conv: 1
        flavor: small
        comment: monitoring for 1.2V of ETROC0

    ...

        BV0:
        pin: 0x12
        conv: 1220
        flavor: small
        comment: monitoring for BV line 0
```
## Developing the code

While developing software for `tamalero`, it is necessary to test new features with the `tests/startup.sh` script before opening a merge request. Both `tamalero` (`setup.sh`) and Vivado must be sourced first. To use `startup.sh`, source the script and pass the appropriate options:
```
Usage: 
	startup
       Options:	
	[-i | --id ID]              Unique ID of CI KCU
	[-f | --firmware FIRMWARE]  Firmware version of KCU
	[-p | --psu PSU:CH]         IP address and channel(s) of Power Supply Unit (will trigger power cycle)
	[-k | --kcu KCU]            IP address of Xilinx KCU
	[-c | --cycle]		    Power cycle PSU (not necessary if -p is set)
	[-h | --help]               Show this screen
```
It is generally recommended to power cycle the Power Supply Units when testing a new feauture with `tests/startup.sh`. An example command is given below:
```
source tests/startup.sh -i 210308B0B4F5 -k 192.168.0.12 -p 192.168.2.3:ch2
```

## Notebook

To use the jupyter notebooks do:
```
source setup.sh
jupyter notebook --no-browser
```
and then on your local machine
```
ssh -N -f -L localhost:8888:localhost:8888 daniel@strange.bu.edu
```
with your username, using the ports as given by the jupyter server.

## Using docker

Setup the docker container with pre-built ipbus:

``` shell
docker run -it --name tamalero danbarto/ubuntu20.04-uhal-python38-tamalero:latest /bin/bash
```

Inside docker, check out this repository with

``` shell
git clone https://gitlab.cern.ch/cms-etl-electronics/module_test_sw.git
```

Setup the paths using `source setup.sh` inside the `module_test_sw` directory and check that ipbus is actually working with `python3 -i -c "import uhal"`.


## Useful block diagrams for connectivity and data flow

[RB v1.6 schematic](http://physics.bu.edu/~wusx/download/ETL_RB/v1.6/ETL_RB_V1.6.PDF)

![module connectivity](docs/module-connectivity.pdf)

## References

[BU EDF](http://ohm.bu.edu/trac/edf/wiki/CMSMipTiming)

### GBT-SCA

[The GBT-SCA, a radiation tolerant ASIC for detector control and monitoring applications in HEP experiments](https://cds.cern.ch/record/2158969?ln=de)

[User Manual](https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA_Manual_2019.002.pdf)

### lpGBT

[Specifications](https://espace.cern.ch/GBT-Project/LpGBT/Specifications/LpGbtxSpecifications.pdf)

[Testing presentation](https://espace.cern.ch/GBT-Project/LpGBT/Presentations/20190118lpGBTnews.pdf)

[User Manual](https://lpgbt.web.cern.ch/lpgbt/v0/)

### KCU105

[Xilinx](https://www.xilinx.com/products/boards-and-kits/kcu105.html)

A simple helper script to configure the KCU105 is available in `kcu_clock_config`. It can be run as:

``` bash
python3 configure_kcu_clock_synth.py
```

It will prompt you to specify the number of the serial port (e.g. `2` for
`/dev/ttyUSB2`), and will give some suggestions about which port it likely is.
If you only have one KCU105 connected to the UART then it is likely the first
choice.

Confirm `y` and it will automatically configure the KCU105.
