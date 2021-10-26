
class FIFO:
    def __init__(self, rb, elink=0):
        self.rb = rb
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_ELINK_SEL"%self.rb.rb, elink)

        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0_MASK"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1_MASK"%self.rb.rb, 0x00)
        

    def set_trigger(self, word0=0x0, word1=0x0, mask0=0x0, mask1=0x0):
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0"%self.rb.rb, word0)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0_MASK"%self.rb.rb, mask0)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1"%self.rb.rb, word1)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1_MASK"%self.rb.rb, mask1)
        

    def reset(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)

    def dump(self, block=255):
        # try forcing trigger?
        res = self.rb.kcu.hw.getNode("DAQ_0.FIFO").readBlock(block)
        self.rb.kcu.hw.dispatch()
        hex_dump = [ '{0:0{1}x}'.format(r,2) for r in res.value() ]
        return hex_dump

