import os
import sys
import serial
import subprocess 

def open_kcu_serial_port(): 

    try: 
        serial.__version__
    except: 
        print("You probably need to install pyserial (pip install pyserial)")
        sys.exit(1) 

    ports = subprocess.Popen(['bash','find_serial_ports.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode().split("\n")[:-1]
    print('\nAvaliable USB ports:')
    print(ports)

    print('\nWelcome to KCU105 clock configuration')
    print('\n')
    usb = input('Which USB port is the board connected to? Type a number:_')
    try: 
        portName = '/dev/ttyUSB'+ str(usb)
        ser = serial.Serial()
        ser.baudrate = 115200
        ser.port = portName
        ser.timeout = 1
        ser.open()
        return ser
    except:
        print('\nERROR: unavaliable USB Port')
        sys.exit(1)

def pprint(line): 
    for l in line: 
        print(l)

def dump(line): 
    print("Unexpected read: ")
    pprint(line)
    sys.exit(1)

def configure_kcu_clocks(): 

    ser = open_kcu_serial_port()
    
    print('\n')
    print(ser.name)
    print("Configuring KCU105 at: " + ser.name)

    if ser.is_open:
        check = input('\nAbout to setup KCU105 Si570, is this okay?  [y/n]:_')

    if (check != 'y'):
        print('\nDid not set up KCU105 Si570\n')
        sys.exit(0)

    ser.write(b'\n')
    line = ser.readlines()

    while b'\r0. Return to Main Menu\r\n' in line:
        print("Returning to main menu")
        ser.write(b'\n0\n')
        line = ser.readlines()

    print('\n Starting \n')
    if b'\r      - Main Menu -\r\n' not in line:
        dump(line)
    else: 
        print('In Main Menu\n')
        ser.write(b'\n1\n')
        line = ser.readlines()

    if b'\r      - Clock Menu -\r\n' not in line:
        dump(line)
    else: 
        print('In Clock Menu\n')
        ser.write(b'\n1\n')
        line = ser.readlines()


    if b'Enter the Si570 frequency (10-810MHz):\r\n' not in line:
        dump(line)
    else: 
        print('Typing frequency...\n')
        ser.write(b'\n320.64\n')
        line = ser.readlines()

    if b'\r3. Save    KCU105 Clock Frequency  to  EEPROM\r\n' not in line:
        dump(line)
    else: 
        print('Entered frequency... Saving')
        ser.write(b'\n3\n')
        line = ser.readlines()

    if b'\r        - Save Menu -\r\n' not in line:
        dump(line)
    else:
        print('\nIn Save Menu\n')
        ser.write(b'\n1\n')
        line = ser.readlines()

    if b'\r        - Save Menu -\r\n' not in line:
        dump(line)
    else:
        ser.write(b'\n0\n')
        print('Loading...\n')
        line = ser.readlines()


    if b'\r      - Clock Menu -\r\n' not in line:
        dump(line)
    else: 
        ser.write(b'\n5\n')
        line = ser.readlines()

    if b'\rSi570  User Clock:  320.64000000 MHz\r\n' not in line:
        dump(line)
    else: 
        print('Saved 320.64 MHz to KCU105 Si570 user clock frequency')
        ser.write(b'\n6\n')
        line = ser.readlines()

    if b'\r      - Options Menu -\r\n' not in line:
        dump(line)
    else: 
        print('\nIn Options Menu\n')
        ser.write(b'\n2\n')
        line = ser.readlines()
        print('Setting up Automatic Restore\n')
        ser.write(b'\n0\n')
        line = ser.readlines()
        ser.write(b'\n0\n')
        line = ser.readlines()
        print('Successful set up of Automatic Restore at Power-Up/Reset\n')

    print('End of Program\n')
    ser.close()


if __name__ == "__main__": 
    configure_kcu_clocks()

