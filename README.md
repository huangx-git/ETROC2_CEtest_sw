# Software for basic ETL RB, PB and module (system) tests: Tamalero

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

- [ipbus](https://github.com/ipbus/ipbus-firmware) for uhal. Needs to be compiled from source for linking with python3 (done on weber.bu.edu, docker image available [here](https://hub.docker.com/repository/docker/danbarto/centos-uhal-py3)).
- [pyyaml](https://pypi.org/project/PyYAML/) for reading the mapping. Install with `pip install pyyaml`.
- [jupyter](https://jupyter.org) for notebook usage. Install with `pip install jupyter`.

## Running the code

To properly set all paths run `source setup.sh`.

A minimal example of usage of this package is given in `test_tamalero.py`, which can be run as:
`ipython -i test_tamalero.py`

The code is organized similar to the physical objects.
The 0th readout board object can be initialzied with
```
rb_0 = ReadoutBoard(0, trigger=False, flavor='small')
```
where `trigger=False` defines that we don't deal with the trigger lpGBT (not yet fully implemented).
The current RB prototype is of the small flavor (3 modules, 12 ETROCs). We anticipate implementing different flavors in the future.

To interact with `rb_0` we need to initialize a control board (KCU105)
```
kcu = KCU(name="my_device",
          ipb_path="ipbusudp-2.0://192.168.0.10:50001",
          adr_table="module_test_fw/address_tables/etl_test_fw.xml")
```
and connect it to the readout board
```
kcu.connect_readout_board(rb_0)
```

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
which reads all ADC lines that are connected, according to the mapping given in [configs/SCA_mapping.yaml](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/blob/master/configs/SCA_mapping.yaml).
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

