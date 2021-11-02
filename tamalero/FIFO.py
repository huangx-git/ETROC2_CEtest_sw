from tamalero.utils import chunk

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
        # needs to be reset twice, dunno
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)
        #print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_ARMED"%self.rb.rb))
        #print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY"%self.rb.rb))
        #self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_FORCE_TRIG" % self.rb.rb, 1)

    def dump(self, block=255):
        # make sure the fifo is not empty
        #while (self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY"%self.rb.rb)):
        #    print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_ARMED"%self.rb.rb))
        #    pass
        res = self.rb.kcu.hw.getNode("DAQ_0.FIFO").readBlock(block)
        self.rb.kcu.hw.dispatch()
        hex_dump = [ '{0:0{1}x}'.format(r,2) for r in res.value() ]
        return hex_dump

    def giant_dump(self, block=3000, subblock=255):
        res = []
        for i in range(block//subblock):
            res += self.dump(block=subblock)
        res += self.dump(block=block%subblock)
        return res

    def dump_to_file(self, hex_dump, filename='dump.hex', n_col=16):
        tmp_chunks = chunk(['35','55'] + hex_dump, n_col)

        # clean the last bytes so that we only keep full events
        for i in range(len(tmp_chunks)):
            if len(tmp_chunks[-1]) < n_col:
                tmp_chunks.pop(-1)
            elif tmp_chunks[-1][0:3] != ['95', '55', '55']:
                tmp_chunks.pop(-1)
            else:
                break

        with open(filename, 'w') as f:
            for line in tmp_chunks:
                for w in line:
                    f.write('%s '%w)
                f.write('\n')

