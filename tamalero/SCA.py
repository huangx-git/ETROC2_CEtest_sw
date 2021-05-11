import random
from tamalero.utils import read_mapping

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

class SCA:

    def __init__(self, rb=0, flavor='small'):
        self.rb = rb
        self.flavor = flavor
        self.adc_mapping = read_mapping('configs/SCA_mapping.yaml', 'adc')

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

    def rw_cmd(self, cmd, channel, data, adr=0x0, transid=0x00):
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
    
        if transid != self.kcu.read_node("READOUT_BOARD_%d.SC.RX.RX_TRANSID" % self.rb):
            print("SCA Read Error :: Transaction ID Does Not Match")
    
    
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
        #import pdb; pdb.set_trace()
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
        binary = bin(val)[:1:-1]
        return int(binary[line])

    def set_gpio(self, line):
        self.configure_control_registers(en_gpio=1)  # enable GPIO
        currently_set = self.rw_reg(SCA_GPIO.GPIO_R_DIRECTION).value()
        currently_set |= (1 << line)
        self.rw_reg(SCA_GPIO.GPIO_W_DIRECTION, currently_set)
        self.rw_reg(SCA_GPIO.GPIO_W_DATAOUT, currently_set)
        return self.read_gpio(line)  # in order to check it is actually set

    def reset_gpio(self):
        self.configure_control_registers(en_gpio=1)  # enable GPIO
        self.rw_reg(SCA_GPIO.GPIO_W_DATAOUT, 0)
        self.rw_reg(SCA_GPIO.GPIO_W_DIRECTION, 0)

    def disable_gpio(self):
        self.configure_control_registers(en_gpio=0)

    def disable_adc(self):
        self.configure_control_registers(en_adc=0)

    def I2C_write(self, I2C_channel, data, servant_adr):
        ##TODO: change data input type to be not a list of bytes (?)
        #1) write byte to DATA register
        if type(data = int):
            data_bytes = [data]
        elif type(data == list):
            data_bytes = data
        else:
            raise("data must be an int or list of ints")
        nbytes = len(data_bytes)
        cmd_codes = [0x40, 0x50, 0x60, 0x70] #[DATA0, DATA1, DATA2, DATA3] 
        data_field = 0x0
        for byte in range(nbytes):
            page = byte // 4
            num_on_page = byte % 4
            data_field = data_field | (data_bytes[byte] << (8* (3 - num_on_page)))
            if num_on_page == 3 or byte == nbytes:
                self.rw_cmd(cmd_codes[page], I2C_channel, data_field)
                data_field = 0x0
        #2) write NBYTES to control register
        self.rw_cmd(0x30, I2C_channel, nbytes) #I2C_W_CTRL = 0x30
        #3) I2C_M_10B_W command(0xE2) with data field = servant address
        self.rw_cmd(0xE2, I2C_channel, servant_adr)
        
    def I2C_read(self, servant_adr=0x48, I2C_channel=0x3, SCA_address=0x0, nbytes=15):
        #1) set NBYTES to recieve in control register
        #   -> using I2C_W_CTRL command (0x30)
        breakpoint()
        self.rw_cmd(0xDA, I2C_channel, 0x0, SCA_address) #clear the servant address
        ctrl_param = (nbytes << 2) | 0x0 #bits 0-1 are FREQ, bits 2-6 is NBYTES
        self.rw_cmd(0x30, I2C_channel, ctrl_param, SCA_address) 
        #2) I2C_M_10B_R (0xE6) with data field = slave address
        status = self.rw_cmd(0xDA, I2C_channel, servant_adr, SCA_address)
        print(status)
        #3) read the data registers
        out_bytes = []


        self.rw_cmd(0x30, I2C_channel, 0x0, SCA_address) #clear the command register
        self.rw_cmd(0xDA, I2C_channel, 0x0, SCA_address) #clear the servant address
        return 0



