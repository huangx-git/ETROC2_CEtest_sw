import os
import time
from tamalero.utils import chunk
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

class FIFO:
    def __init__(self, rb, elink=0, ETROC='ETROC1'):
        self.rb = rb
        self.ETROC = ETROC
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_ELINK_SEL"%self.rb.rb, elink)
        self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.DL_SRC"%self.rb.rb, 3)


        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0_MASK"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1_MASK"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG2"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG2_MASK"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG3"%self.rb.rb, 0x00)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG3_MASK"%self.rb.rb, 0x00)

        with open(os.path.expandvars('$TAMALERO_BASE/configs/dataformat.yaml')) as f:
            self.dataformat = load(f, Loader=Loader)[ETROC]

        with open(os.path.expandvars('$TAMALERO_BASE/configs/fast_commands.yaml')) as f:
            self.fast_commands = load(f, Loader=Loader)[ETROC]

        self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_IDLE"%self.rb.rb, self.fast_commands['IDLE'])
        self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_DATA"%self.rb.rb, self.fast_commands['L1A'])
        

    def set_trigger(self, word0=0x0, word1=0x0, word2=0x0, word3=0x0, mask0=0x0, mask1=0x0, mask2=0x0, mask3=0x0):
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0"%self.rb.rb, word0)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG0_MASK"%self.rb.rb, mask0)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1"%self.rb.rb, word1)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG1_MASK"%self.rb.rb, mask1)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG2"%self.rb.rb, word2)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG2_MASK"%self.rb.rb, mask2)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG3"%self.rb.rb, word3)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG3_MASK"%self.rb.rb, mask3)
        

    def reset(self):
        # needs to be reset twice, dunno
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)
        #print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_ARMED"%self.rb.rb))
        #print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY"%self.rb.rb))
        #self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_FORCE_TRIG" % self.rb.rb, 1)
        if self.ETROC == 'ETROC2':
            self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_PULSE"%self.rb.rb, 0x01)  # FIXME confirm this

    def make_word(self, bytes):
        if len(bytes) == 5:
            return bytes[0] << 32 | bytes[1] << 24 | bytes[2] << 16 | bytes[3] << 8 | bytes[4]
        return 0

    def compare(self, byte, frame, mask):
        return (byte & mask) == frame

    def align_stream(self, stream):
        frames = []
        masks = []
        for shift in [32, 24, 16, 8, 0]:
            frames.append((self.dataformat['identifiers']['header']['frame'] & ((self.dataformat['identifiers']['header']['mask'] >> shift) & 0xFF) << shift) >> shift)
            masks.append((self.dataformat['identifiers']['header']['mask'] >> shift) & 0xFF)

        for i in range(250):
            word = stream[i:i+5]
            res = list(map(self.compare, word, frames, masks))
            if sum(res) == 5:
                return stream[i:]
        return []

    def dump(self, block=255, format=True):
        #self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_PULSE"%self.rb.rb, 0x01)  # FIXME this is not needed I think
        for i in range(10):
            if self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY"%self.rb.rb).value() < 1: break
        res = self.rb.kcu.hw.getNode("DAQ_0.FIFO").readBlock(block)
        try:
            self.rb.kcu.hw.dispatch()
            return res.value()
        except:
            # NOTE: not entirely understood, but it seems this happens if FIFO is (suddenly?) empty
            return []

    def giant_dump(self, block=3000, subblock=255, format=True):
        stream = []
        for i in range(block//subblock):
            stream += self.dump(block=subblock, format=format)
        stream += self.dump(block=block%subblock, format=format)
        stream = self.align_stream(stream)
        if format:
            hex_dump = [ '{0:0{1}x}'.format(r,2) for r in stream ]
            return hex_dump
        else:
            return [ self.make_word(c) for c in chunk(stream, n=5) if len(c)==5 ]
        return res

    def wipe(self, hex_dump, trigger_words=['35', '55'], integer=False):
        '''
        after a dump you need to wipe
        '''
        tmp_chunks = chunk(trigger_words + hex_dump, int(self.dataformat['nbits']/8))

        # clean the last bytes so that we only keep full events
        for i in range(len(tmp_chunks)):
            if len(tmp_chunks[-1]) < self.dataformat['nbits']/8:
                tmp_chunks.pop(-1)
            else:
                break

        if integer:
            tmp_chunks = [ int(''.join(line),16) for line in tmp_chunks ]

        return tmp_chunks

    def dump_to_file(self, hex_dump, filename='dump.hex'):
        with open(filename, 'w') as f:
            for line in hex_dump:
                for w in line:
                    f.write('%s '%w)
                f.write('\n')

