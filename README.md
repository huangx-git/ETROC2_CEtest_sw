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


## Setup and Dependencies

- [ipbus](https://github.com/ipbus/ipbus-firmware) for uhal

## Running the code

`ipython -i test_tamalero.py`

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

