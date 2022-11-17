import os
import random
from tamalero.utils import read_mapping
import time

class SCA_CRB:
    # 0 is reserved
    ENSPI  = 1
    ENGPIO = 2
    ENI2C0 = 3
    ENI2C1 = 4
    ENI2C2 = 5
    ENI2C3 = 6
    ENI2C4 = 7

class SCA_CRC:
    ENI2C5 = 0
    ENI2C6 = 1
    ENI2C7 = 2
    ENI2C8 = 3
    ENI2C9 = 4
    ENI2CA = 5
    ENI2CB = 6
    ENI2CC = 7

class SCA_CRD:
    ENI2CD = 0
    ENI2CE = 1
    ENI2CF = 2
    ENJTAG = 3
    ENADC  = 4
    ENDAC  = 6

class SCA_CONTROL:
    CTRL_R_ID  = 0x14D1  # this is SCA V2
    CTRL_W_CRB = 0x0002
    CTRL_R_CRB = 0x0003
    CTRL_W_CRC = 0x0004
    CTRL_R_CRC = 0x0005
    CTRL_W_CRD = 0x0006
    CTRL_R_CRD = 0x0007
    CTRL_R_SEU = 0x13F1
    CTRL_C_SEU = 0x13F1

class SCA_GPIO:
    GPIO_W_DATAOUT   = 0x0210
    GPIO_R_DATAOUT   = 0x0211
    GPIO_R_DATAIN    = 0x0201
    GPIO_W_DIRECTION = 0x0220
    GPIO_R_DIRECTION = 0x0221

class SCA_ADC:
    ADC_GO     = 0x1402
    ADC_W_MUX  = 0x1450
    ADC_R_MUX  = 0x1451
    ADC_W_CURR = 0x1460
    ADC_R_CURR = 0x1461
    ADC_W_GAIN = 0x1410
    ADC_R_GAIN = 0x1411
    ADC_R_DATA = 0x1421
    ADC_R_RAW  = 0x1431
    ADC_R_OFS  = 0x1441

class SCA_JTAG:
    # JTAG COMMANDS
    JTAG_W_CTRL = 0x1380
    JTAG_R_CTRL = 0x1381
    JTAG_W_FREQ = 0x1390
    JTAG_R_FREQ = 0x1391
    JTAG_W_TDO0 = 0x1300
    JTAG_R_TDI0 = 0x1301
    JTAG_W_TDO1 = 0x1310
    JTAG_R_TDI1 = 0x1311
    JTAG_W_TDO2 = 0x1320
    JTAG_R_TDI2 = 0x1321
    JTAG_W_TDO3 = 0x1330
    JTAG_R_TDI3 = 0x1331
    JTAG_W_TMS0 = 0x1340
    JTAG_R_TMS0 = 0x1341
    JTAG_W_TMS1 = 0x1350
    JTAG_R_TMS1 = 0x1351
    JTAG_W_TMS2 = 0x1360
    JTAG_R_TMS2 = 0x1361
    JTAG_W_TMS3 = 0x1370
    JTAG_R_TMS3 = 0x1371
    JTAG_ARESET = 0x13C0
    JTAG_GO     = 0x13A2
    JTAG_GO_M   = 0x13B0

class SCA_I2C:
    # I2C commands
    I2C_W_CTRL = 0x30 # write control register
    I2C_R_CTRL = 0x31 # read control register
    I2C_R_STR  = 0x11 # read status register
    I2C_S_7B_W = 0x82 # single byte write
    I2C_S_7B_R = 0x86 # single byte read
    I2C_M_7B_R = 0xDE # multi-byte read
    I2C_M_7B_W = 0xDA # multi-byte write
    I2C_W_DATA0 = 0x40 # write to data register 0
    I2C_W_DATA1 = 0x50 # write to data register 1
    I2C_W_DATA2 = 0x60 # write to data register 2
    I2C_W_DATA3 = 0x70 # write to data register 3
    I2C_R_DATA0 = 0x41 # read from data register 0
    I2C_R_DATA1 = 0x51 # read from data register 1
    I2C_R_DATA2 = 0x61 # read from data register 2
    I2C_R_DATA3 = 0x71 # read from data register 3
    I2C_RW_DATA_OFFSET = 16 # offset to access data register 1, 2, 3


class SCA:

    def __init__(self, rb=0, flavor='small'):
        self.rb = rb
        self.flavor = flavor
        self.err_count = 0
        self.adc_mapping = read_mapping(os.path.expandvars('$TAMALERO_BASE/configs/SCA_mapping.yaml'), 'adc')
        self.gpio_mapping = read_mapping(os.path.expandvars('$TAMALERO_BASE/configs/SCA_mapping.yaml'), 'gpio')

    def connect_KCU(self, kcu):
        self.kcu = kcu

    def reset(self):
        self.kcu.action("READOUT_BOARD_%d.SC.START_RESET" % self.rb)
    
    def connect(self):
        self.kcu.action("READOUT_BOARD_%d.SC.START_CONNECT" % self.rb)

    def enable(self, state=1):
        self.kcu.write_node("READOUT_BOARD_%d.SC.SCA_ENABLE" % self.rb, state)

    def rw_reg(self, reg, data=0x0, adr=0x00, transid=0x00):
        cmd = reg & 0xFF
        channel = (reg >> 8) & 0xFF
        return self.rw_cmd(cmd, channel, data, adr, transid)

    def rw_cmd(self, cmd, channel, data, adr=0x0, transid=0x00, time_out=0.3):
        """
        adr = chip address (0x0 by default)
        """

        if transid == 0:
            transid = random.randint(1, 2**8-2)  # transid of 0 or 255 gives error

        # request packet structure
        # sof
        # address : destination packet address (chip id)
        # control : connect/sabm, reset, test
        # {
        #  transid
        #  channel
        #  length
        #  command
        #  data[31:0]
        # }
        # fcs
        # eof
    
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_CHANNEL" % self.rb, channel)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_CMD" % self.rb, cmd)
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_ADDRESS" % self.rb, adr)
    
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_TRANSID" % self.rb, transid)
    
        self.kcu.write_node("READOUT_BOARD_%d.SC.TX_DATA" % self.rb, data)
        self.kcu.action("READOUT_BOARD_%d.SC.START_COMMAND" % self.rb)
    
        # reply packet structure
        # sof
        # address
        # control
        # {
        #  transid
        #  channel
        #  error
        #  length
        #  data
        # }
        # fcs
        # eof
    
        # TODO: read reply
        err = self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_ERR" % self.rb)  # 8 bit
        if err > 0:
            if self.err_count < 10:
                self.rw_cmd(cmd, channel, data, adr=adr, transid=transid)
                self.err_count += 1
            else:
                print ("Failed %s times: %s. Last error:"%self.err_count)
                if (err & 0x1):
                    print("SCA Read Error :: Generic Error Flag")
                if (err & 0x2):
                    print("SCA Read Error :: Invalid Channel Request")
                if (err & 0x4):
                    print("SCA Read Error :: Invalid Command Request")
                if (err & 0x8):
                    print("SCA Read Error :: Invalid Transaction Number Request")
                if (err & 0x10):
                    print("SCA Read Error :: Invalid Length")
                if (err & 0x20):
                    print("SCA Read Error :: Channel Not Enabled")
                if (err & 0x40):
                    print("SCA Read Error :: Command In Treatment")
        else:
            self.err_count = 0

        # NOTE I2C transaction can be slow, so try reading the transid several times before it times out
        start_time = time.time()
        while not transid == self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_TRANSID" % self.rb):
            if time.time() - start_time > time_out:
                print("SCA Read Error :: Transaction ID Does Not Match")
                print("SCA Read Error :: Resetting RX/TX")
                self.kcu.write_node("READOUT_BOARD_%d.SC.RX_RESET" % self.rb, 0x01)
                self.kcu.write_node("READOUT_BOARD_%d.SC.TX_RESET" % self.rb, 0x01)
                raise TimeoutError("SCA Error :: Transaction timed out.")

        return self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_DATA" % self.rb)  # 32 bit read data
    
        self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_RECEIVED" % self.rb)  # flag pulse
        self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_CHANNEL" % self.rb)  # channel reply
        self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_LEN" % self.rb)
        self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_ADDRESS" % self.rb)
        self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_CONTROL" % self.rb)

    def configure_control_registers(self, en_spi=0, en_gpio=0, en_i2c=0, en_adc=0, en_dac=0):
    
        ENI2C0  = (en_i2c >> 0) & 0x1
        ENI2C1  = (en_i2c >> 1) & 0x1
        ENI2C2  = (en_i2c >> 2) & 0x1
        ENI2C3  = (en_i2c >> 3) & 0x1
        ENI2C4  = (en_i2c >> 4) & 0x1
        ENI2C5  = (en_i2c >> 5) & 0x1
        ENI2C6  = (en_i2c >> 6) & 0x1
        ENI2C7  = (en_i2c >> 7) & 0x1
        ENI2C8  = (en_i2c >> 8) & 0x1
        ENI2C9  = (en_i2c >> 9) & 0x1
        ENI2CA  = (en_i2c >> 10) & 0x1
        ENI2CB  = (en_i2c >> 11) & 0x1
        ENI2CC  = (en_i2c >> 12) & 0x1
        ENI2CD  = (en_i2c >> 13) & 0x1
        ENI2CE  = (en_i2c >> 14) & 0x1
        ENI2CF  = (en_i2c >> 15) & 0x1
    
        crb = 0
        crb |= en_spi << SCA_CRB.ENSPI
        crb |= en_gpio << SCA_CRB.ENGPIO
        crb |= ENI2C0 << SCA_CRB.ENI2C0
        crb |= ENI2C1 << SCA_CRB.ENI2C1
        crb |= ENI2C2 << SCA_CRB.ENI2C2
        crb |= ENI2C3 << SCA_CRB.ENI2C3
        crb |= ENI2C4 << SCA_CRB.ENI2C4
    
        crc = 0
        crc |= ENI2C5 << SCA_CRC.ENI2C5
        crc |= ENI2C6 << SCA_CRC.ENI2C6
        crc |= ENI2C7 << SCA_CRC.ENI2C7
        crc |= ENI2C8 << SCA_CRC.ENI2C8
        crc |= ENI2C9 << SCA_CRC.ENI2C9
        crc |= ENI2CA << SCA_CRC.ENI2CA
        crc |= ENI2CB << SCA_CRC.ENI2CB
        crc |= ENI2CC << SCA_CRC.ENI2CC
    
        crd = 0
        crd |= ENI2CD << SCA_CRD.ENI2CD
        crd |= ENI2CE << SCA_CRD.ENI2CE
        crd |= ENI2CF << SCA_CRD.ENI2CF
        crd |= en_adc << SCA_CRD.ENADC
        crd |= en_dac << SCA_CRD.ENDAC

        self.rw_reg(SCA_CONTROL.CTRL_W_CRB, crb << 24)
        self.rw_reg(SCA_CONTROL.CTRL_W_CRC, crc << 24)
        self.rw_reg(SCA_CONTROL.CTRL_W_CRD, crd << 24)
    
        crb_rd = self.rw_reg(SCA_CONTROL.CTRL_R_CRB) >> 24
        crc_rd = self.rw_reg(SCA_CONTROL.CTRL_R_CRC) >> 24
        crd_rd = self.rw_reg(SCA_CONTROL.CTRL_R_CRD) >> 24
    
        if (crb != crb_rd or crc != crc_rd or crd != crd_rd):
            print("SCA Control Register Readback Error, Not configured Correctly")
            print("CRB wr=%02X, rd=%02X" % (crb, crb_rd))
            print("CRC wr=%02X, rd=%02X" % (crc, crc_rd))
            print("CRD wr=%02X, rd=%02X" % (crd, crd_rd))

    def read_adc(self, MUX_reg = 0):
        self.configure_control_registers(en_adc=1) #enable ADC
        self.rw_reg(SCA_ADC.ADC_W_MUX, MUX_reg) #configure register we want to read
        val = self.rw_reg(SCA_ADC.ADC_GO, 0x01).value() #execute and read ADC_GO command
        self.rw_reg(SCA_ADC.ADC_W_MUX, 0x0) #reset register to default (0)
        return val

    def read_adcs(self): #read and print all adc values
        adc_dict = self.adc_mapping
        for adc_reg in adc_dict.keys():
            pin = adc_dict[adc_reg]['pin']
            comment = adc_dict[adc_reg]['comment']
            value = self.read_adc(pin)
            input_voltage = value / (2**12 - 1) * adc_dict[adc_reg]['conv']
            out_string = "register: {0}".format(adc_reg).ljust(22)+\
            "pin: {0}".format(pin).ljust(10)+"reading: {0}".format(value).ljust(16)+\
            "in voltage: {0:.4f}".format(input_voltage).ljust(22) + "comment: '{0}'".format(comment)
            print(out_string)

    def read_temp(self):
        # not very precise (according to manual), but still useful.
        return ((self.read_adc(31)/2**12)*1000 - 716)/-1.829

    def read_gpio(self, line):
        self.configure_control_registers(en_gpio=1)  # enable GPIO
        val = self.rw_reg(SCA_GPIO.GPIO_R_DATAIN).value()
        return int((val >> line) & 1)

    def set_gpio(self, line, to=1):
        self.configure_control_registers(en_gpio=1)  # enable GPIO
        currently_set = self.rw_reg(SCA_GPIO.GPIO_R_DATAOUT).value()
        if (currently_set & (1 << line)) and to==0:
            currently_set ^= (1 << line)
        elif to==1:
            currently_set |= (1 << line)
        #self.rw_reg(SCA_GPIO.GPIO_W_DIRECTION, currently_set)
        self.rw_reg(SCA_GPIO.GPIO_W_DATAOUT, currently_set)
        return self.read_gpio(line)  # in order to check it is actually set

    def set_gpio_direction(self, line, to=1):
        self.configure_control_registers(en_gpio=1)  # enable GPIO
        currently_set = self.rw_reg(SCA_GPIO.GPIO_R_DIRECTION).value()
        if (currently_set & (1 << line)) and to==0:
            currently_set ^= (1 << line)
        elif to==1:
            currently_set |= (1 << line)
        self.rw_reg(SCA_GPIO.GPIO_W_DIRECTION, currently_set)
        currently_set = self.rw_reg(SCA_GPIO.GPIO_R_DIRECTION).value()
        return (currently_set >> line) & 1  # in order to check it is actually set

    def reset_gpio(self):
        self.configure_control_registers(en_gpio=1)  # enable GPIO
        self.rw_reg(SCA_GPIO.GPIO_W_DATAOUT, 0)
        self.rw_reg(SCA_GPIO.GPIO_W_DIRECTION, 0)

    def disable_gpio(self):
        self.configure_control_registers(en_gpio=0)

    def disable_adc(self):
        self.configure_control_registers(en_adc=0)

    def config_gpios(self, verbose=False): #read and print all adc values
        gpio_dict = self.gpio_mapping
        if verbose:
            print("Configuring SCA GPIO Pins...")
        for gpio_reg in gpio_dict.keys():
            pin         = gpio_dict[gpio_reg]['pin']
            direction   = int(gpio_dict[gpio_reg]['direction'] == 'out')
            comment     = gpio_dict[gpio_reg]['comment']
            default     = gpio_dict[gpio_reg]['default']
            if verbose:
                print("Setting SCA GPIO pin %s (%s) to %s"%(pin, comment, gpio_dict[gpio_reg]['direction']))
            self.set_gpio_direction(pin, direction)
            self.set_gpio(pin, default)

    def get_I2C_channel(self, channel):
        # this only works for channel 0-4 right now, enough for the tests. Needs to be fixed!
        return getattr(SCA_CRB, "ENI2C%s"%channel)

    def I2C_write(self, reg=0x0, val=0x0, master=3, slave_addr=0x48, adr_nbytes=2):
        # wrapper function to have similar interface as lpGBT I2C_write
        # enable corresponding channel. only one enabled at a time
        self.configure_control_registers(en_i2c=(1<<master))
        adr_bytes = [ ((reg >> (8*i)) & 0xff) for i in range(adr_nbytes) ]
        if isinstance(val, int):
            data_bytes = [val]
        elif isinstance(val, list):
            data_bytes = val
        else:
            raise("data must be an int or list of ints")
        self.I2C_write_multi(adr_bytes + data_bytes, channel=master, servant=slave_addr)

    def I2C_read(self, reg=0x0, master=3, slave_addr=0x48, nbytes=1, adr_nbytes=2):
        # wrapper function to have similar interface as lpGBT I2C_read
        if nbytes > 1:
            return self.I2C_read_multi(channel=master, servant=slave_addr, reg=reg, nbytes=nbytes)
        else:
            return self.I2C_read_single_byte(channel=master, servant=slave_addr, reg=reg)

    def I2C_read_single_byte(self, channel=3, servant=0x48, reg=0x00):
        # enable corresponding channel. only one enabled at a time
        self.configure_control_registers(en_i2c=(1<<channel))
        
        # write to the pointer reg
        self.I2C_write_single_byte(channel=channel, servant=servant, data=reg)

        # single byte read
        res = self.rw_cmd(SCA_I2C.I2C_S_7B_R, self.get_I2C_channel(channel), servant<<24, 0x0).value()
        status = (res >> 24)
        success = (status & 4)
        if success:
            return (res >> 16) & 255
        else:
            #print ("Read not successful")
            return False

    def I2C_write_single_byte(self, channel, servant, data):
        #enable channel
        self.configure_control_registers(en_i2c=(1<<channel))
        #single byte write
        data_field = (servant<<24) | ((data & 255) << 16) #[31:24] is servant address, [23:16] is data byte
        res = self.rw_cmd(SCA_I2C.I2C_S_7B_W, self.get_I2C_channel(channel), data_field).value()
        status = res >> 24
        success = status & 4
        if success:
            return True
        else:
            #print("write not successful: status = {}".format(status))
            return False

    def I2C_write_ctrl(self, channel, data):
        #enable channel
        self.configure_control_registers(en_i2c=(1<<channel))
        #write control register
        data_field = data << 24
        res = self.rw_cmd(SCA_I2C.I2C_W_CTRL, self.get_I2C_channel(channel), data_field).value()
        return #no status register to return?

    def I2C_read_ctrl(self, channel):
        #enable channel
        self.configure_control_registers(en_i2c=(1<<channel))
        #read control register
        res = self.rw_cmd(SCA_I2C.I2C_R_CTRL, self.get_I2C_channel(channel), 0x0).value()
        return res >> 24

    def I2C_read_multi(self, channel=3, servant=0x48, nbytes=15, reg=0x0):
        #enable channel
        self.configure_control_registers(en_i2c=(1<<channel))
        #configure NBYTES in the control register
        self.I2C_write_ctrl(channel, nbytes<<2)
        # write to the pointer reg
        self.I2C_write_single_byte(channel=channel, servant=servant, data=reg)
        #multi-byte read
        start_time = time.time()
        cmd_res = self.rw_cmd(SCA_I2C.I2C_M_7B_R, self.get_I2C_channel(channel), (servant<<24)).value()
        status = cmd_res >> 24
        success = status & 4
        while not success:
            cmd_res = self.rw_cmd(SCA_I2C.I2C_M_7B_R, self.get_I2C_channel(channel), (servant<<24)).value()
            status = cmd_res >> 24
            success = status & 4
            if time.time() - start_time > 0.1:
                raise TimeoutError("I2C_M_7B_R not successful, status = {}".format(status))

        #read data register
        #we are counting backwards because we need to call I2C_R_DATA3 to get data bytes 0, 1, 2, 3, and so on.
        #[I2C_R_DATA3, I2C_R_DATA2, I2C_R_DATA1, I2C_R_DATA0]
        data_registers = [SCA_I2C.I2C_R_DATA3 - SCA_I2C.I2C_RW_DATA_OFFSET * n for n in range(((nbytes-1)//4) + 1)]
        out_bytes = []

        for page in range((((nbytes-1)//4) + 1)):
            page_value = self.rw_cmd(data_registers[page], self.get_I2C_channel(channel), 0x0).value() #execute I2C_R_DATA[3,2,1,0]
            for byte in range(4):
                if (byte + 4*page) < nbytes:
                    mask = 255 << (8 * (3 - byte))
                    return_byte = (page_value & mask) >> (8 * (3 - byte))
                    out_bytes.append(return_byte)

        return out_bytes

    def I2C_write_multi(self, data, channel=3, servant=0x48):
        if not type(data) == list:
            data = [data]
        nbytes = len(data)
        #enable channel
        self.configure_control_registers(en_i2c=(1<<channel))
        #configure NBYTES in the control register
        self.I2C_write_ctrl(channel, nbytes<<2)
        #begin writing to the data registers [I2C_W_DATA0, I2C_W_DATA1, I2C_W_DATA2, I2C_W_DATA3]
        data_registers = [SCA_I2C.I2C_W_DATA0 + SCA_I2C.I2C_RW_DATA_OFFSET * n for n in range(((nbytes-1)//4) + 1)]
        for page in range(((nbytes-1)//4) + 1):
            cmd_val = 0x0
            for byte in range(4):
                if (byte + (4 * page)) < nbytes:
                    write_byte = data[byte + (4*page)] << (8 * (3 - byte))
                    cmd_val = cmd_val + write_byte #append the data byte to the correct position in the command value
            self.rw_cmd(data_registers[page], self.get_I2C_channel(channel), cmd_val)

        #once data registers are filled, execute I2C_M_7B_W
        start_time = time.time()
        data_field = (servant<<24)
        cmd_res = self.rw_cmd(SCA_I2C.I2C_M_7B_W, self.get_I2C_channel(channel), data_field).value()
        status = cmd_res >> 24
        success = status & 4
        while not success:
            cmd_res = self.rw_cmd(SCA_I2C.I2C_M_7B_W, self.get_I2C_channel(channel), data_field).value()
            status = cmd_res >> 24
            success = status & 4
            if time.time() - start_time > 0.3:
                raise TimeoutError("I2C_M_7B_W not successful, status = {}".format(status))


    def I2C_status(self, channel=3, verbose=1):
        # returns whether last transaction was successful
        self.configure_control_registers(en_i2c=(1<<channel))
        res = self.rw_cmd(SCA_I2C.I2C_R_STR, self.get_I2C_channel(channel), 0x0, 0x0).value()
        status = (res >> 24)
        success = (status & (1<<2)) >> 2 # bit 2 is for success
        if success:
            if verbose:
                print ("Last transaction successful!")
            else:
                pass
        else:
            print ("Last transaction not successful!")
        if (status & (1<<3)):
            print ("SDA/I2C bus broken")
        if (status & (1<<5)):
            print ("Invalid command")
        if (status & (1<<6)):
            print ("Operation not acknowledged by servant")

        return success

    def read_temp_i2c(self, channel=3):
        res = self.I2C_read_multi(channel=channel, servant = 0x48, nbytes=2)
        temp_dig = (res[0] << 4) + (res[1] >> 4)
        return temp_dig*0.0625
