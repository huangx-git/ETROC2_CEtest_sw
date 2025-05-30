# Quick Start Guidance for ETROC2 Cabel and Eliminator Test Stand Setup

## Preparation

Operation system, using **Ubuntu 20.04 LTS**. Newer Ubuntu versions have trouble with the IPBUS software compilation.

Python environment, tested on **python 3.8.10**.

**Vivado 2021.1** version of the package. [Vivado ML Edition - 2021.1](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools/archive.html) Choose _Xilinx Unified Installer 2021.1: Linux Self Extracting Web Installer (BIN - 301.28 MB)._ Enterprise version. You will likely need to install this package sudo apt install libtinfo5 otherwise the installation will not complete, hanging on the finishing stage of generating installed device list.

To install the Linux driver, do the [following](https://docs.amd.com/r/2021.1-English/ug973-vivado-release-notes-install-license/Installing-Cable-Drivers): 
```
${vivado_install_dir}/data/xicom/cable_drivers/lin64/install_script/install_drivers/install_drivers
```


## Software clone
 Install the software with all its dependencies except IPbus:

```
git clone https://github.com/huangx-git/ETROC2_CEtest_sw.git
```

## IPbus installation

First, update the system and install git and python

```
sudo apt update
sudo apt upgrade
sudo apt install git
sudo apt install python3.8
```

THe update step might do the python3.8, but this is fine.

Next, install the packages needed to compile the ipbus software

```sudo apt-get install -y make erlang g++ libboost-all-dev libpugixml-dev python-all-dev rsyslog```

with the needed packages ready, download, compile, and install ipbus
```
git clone --depth=1 -b v2.8.3 --recurse-submodules https://github.com/ipbus/ipbus-software.git
cd ipbus-software
sudo make PYTHON=python3
sudo make install PYTHON=python3
```
With this finished, check that the install worked. Use the first command to temporarily set the ipbus path, then open a session of python and import uhal
```
export LD_LIBRARY_PATH=/opt/cactus/lib:$LD_LIBRARY_PATH
python3
import uhal
```
If there are no errors while importing, everthing worked and you can continue the installation process.

Control hub is part of the IPbus package and can be started with e.g. ``` /opt/cactus/bin/controlhub_start```

Check the control hub's status using ``` /opt/cactus/bin/controlhub_status```

## KCU105 Loading Firmware

Assuming you have set up the clock of KCU105 board,the KCU105 firmware can be loaded following procedures described [here](https://etl-rb.docs.cern.ch/Firmware/rb-firmware/#firmware-for-kcu-105).

## KCU105 Network Configuration
The IP address of the board is set by a 4 bit switch SW12. The 4 bit switch is interpreted as a 4 bit offset which is added to a base IP address (`192.168.0.10+offset`). and a MAC of `00_08_20_83_53_00+offset`.
Next, configure the ethernet of your PC to be able to communicate with the board. Open your PC network settings, naviate to the IPv4 tab, switch to 'Manual'. Set the address to `192.168.0.0` and Netmask to `255.255.0.0` can be any value not already taken on the network. 

## Quick Test
Run the Jupyter Notebook file of __etroc2_ceTest.ipynb__ step by step, if no error occurs, that mean you have the uplink and downlink set up successfully.
