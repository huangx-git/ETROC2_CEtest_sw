import random

class SCA_CRB:
    ENSPI  = 0
    ENGPIO = 1
    ENI2C0 = 2
    ENI2C1 = 3
    ENI2C2 = 4
    ENI2C3 = 5
    ENI2C4 = 6

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

    def __init__(self, rb=0):
        self.rb = rb

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
            transid = random.randint(0, 2**8-1)

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
