import os
import time
from tamalero.utils import chunk
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def revbits(x):
    return int(f'{x:08b}'[::-1],2)

def just_read(rb, link, daq=True):
    '''
    very simple function that just reads whatever comes out of a link, no matter the pattern.
    This might be broken in v1.2.2 or later, needs some more investigation
    '''
    fifo = FIFO(rb, links=[{'elink':link, 'lpgbt':0 if daq else 1}], ETROC='ETROC2')
    # just keep the default trigger words
    fifo.set_trigger([0x0]*10, [0x0]*10)
    #fifo.reset()
    #fifo.reset()
    res = fifo.dump(block=255, format=True, daq=daq)
    return res

def just_read_daq(rb, link, lpgbt, fixed_pattern=False, trigger_rate=0, send_l1a=True, l1a_count=1):
    '''
    very simple function that just reads whatever comes out of a link, no matter the pattern
    this is tested with v1.2.2 @ BU test stand, DAQ elink 2 and trigger elink 20.
    With firmware v1.2.2 this function does not care about uplink alignment anymore.
    Frames are automatically aligned by bitslipping in the firmware.
    NOTE: It seems as if the last word is read out if the FIFO is otherwise empty, resulting in weird trailers.
    FIXME: Fix the trailing trailers when the FIFO has no more data.
    trigger_rate is roughly in Hertz
    '''
    import numpy as np
    fifo = FIFO(rb, links=[{'elink':link, 'lpgbt':lpgbt}], ETROC='ETROC2')

    if fixed_pattern and rb.kcu.firmware_version['minor'] >= 2 and rb.kcu.firmware_version['patch'] >= 3 :
        fifo.use_fixed_pattern()

    if trigger_rate>0:
        rate = fifo.set_trigger_rate(trigger_rate)
        print (f"Trigger rate is currently {rate} Hz")

    fifo.reset()
    #time.sleep(5)  # might be useful if the L1A generator works

    if l1a_count>=1:
        fifo.send_l1a(count=l1a_count)

    res = fifo.dump_daq(block=3000)

    if rb.kcu.firmware_version['minor'] >= 2 and rb.kcu.firmware_version['patch'] >= 3:
        fifo.use_etroc_data()

    empty_frame_mask = np.array(res[0::2]) > (2**8)  # masking empty fifo entries
    len_cut = min(len(res[0::2]), len(res[1::2]))  # ensuring equal length of arrays downstream
    if len(res) > 0:
        return list (np.array(res[0::2])[:len_cut][empty_frame_mask[:len_cut]] | (np.array(res[1::2]) << 32)[:len_cut][empty_frame_mask[:len_cut]])
    else:
        return []

def manual_link_scan(lpgbt=0, zero_supress=True):
    rb_0.kcu.write_node("READOUT_BOARD_0.BITSLIP_AUTO_EN", 0x0)

    if not zero_supress:
        rb_0.kcu.write_node("READOUT_BOARD_0.ZERO_SUPRESS", 0x0)

    for i in range(24):
        print (f'\n\nLink {i}')
        for j in range(40):
            rb_0.kcu.write_node("READOUT_BOARD_0.ETROC_BITSLIP", 1<<i)
            just_read_daq(rb_0, i, 0)
            print (just_read_daq(rb_0, i, 0))

    # Back to defaults (zero supression on for all links)
    rb_0.kcu.write_node("READOUT_BOARD_0.ZERO_SUPRESS", 2**28-1)
    rb_0.kcu.write_node("READOUT_BOARD_0.BITSLIP_AUTO_EN", 0x1)

def get_event(data_frame, data_words):
    for word in data_words:
        print (data_frame.read(word))

class FIFO:
    #def __init__(self, rb, elink=0, ETROC='ETROC1', lpgbt=0):
    def __init__(self, rb, links=[{'elink':0, 'lpgbt':0}], ETROC='ETROC1'):
        self.rb = rb
        self.ETROC = ETROC
        self.nlinks = len(links)
        for i, link in enumerate(links):
            #print (f"Setting FIFO {i} to read from elink {link['elink']} and lpGBT {link['lpgbt']}.")  # This is too noisy
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_ELINK_SEL%i"%(self.rb.rb, i), link['elink'])
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_LPGBT_SEL%i"%(self.rb.rb, i), link['lpgbt'])

        with open(os.path.expandvars('$TAMALERO_BASE/configs/dataformat.yaml')) as f:
            self.dataformat = load(f, Loader=Loader)[ETROC]

        with open(os.path.expandvars('$TAMALERO_BASE/configs/fast_commands.yaml')) as f:
            self.fast_commands = load(f, Loader=Loader)[ETROC]

    def turn_on_zero_surpress(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb, 0x1)

    def turn_off_zero_surpress(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb, 0x0)

    def use_fixed_pattern(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.RX_FIFO_DATA_SRC"%self.rb.rb, 0x1)

    def use_etroc_data(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.RX_FIFO_DATA_SRC"%self.rb.rb, 0x0)

    def set_trigger_rate(self, rate):
        # set rate in Hz
        self.rb.kcu.write_node("SYSTEM.L1A_RATE", rate*100)
        time.sleep(0.5)
        rate = self.rb.kcu.read_node("SYSTEM.L1A_RATE_CNT").value()
        return rate

    def send_l1a(self, count=1):
        for i in range(count):
            self.rb.kcu.write_node("SYSTEM.L1A_PULSE", 1)

    def reset(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET" % self.rb.rb, 0x01)

    def make_word(self, bytes, reversed=False):
        if len(bytes) == 5 and not reversed:
            return bytes[0] << 32 | bytes[1] << 24 | bytes[2] << 16 | bytes[3] << 8 | bytes[4]
        elif len(bytes) == 5 and reversed:
            return bytes[0] | bytes[1] << 8 | bytes[2] << 16 | bytes[3] << 24 | bytes[4] << 32
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

    def dump(self, block=255, format=True, daq=0):

        for i in range(10):
            if self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY%i"%(self.rb.rb, daq)).value() < 1: break  # FIXME I'm lazy. This should be done for all (?) FIFOS
        res = self.rb.kcu.hw.getNode("DAQ_%i.FIFO"%daq).readBlock(block)
        try:
            self.rb.kcu.hw.dispatch()
            return res.value()
        except:
            # NOTE: not entirely understood, but it seems this happens if FIFO is (suddenly?) empty
            return []

    def dump_daq(self, block=255):

        res = self.rb.kcu.hw.getNode("DAQ_RB0.FIFO").readBlock(block)
        try:
            self.rb.kcu.hw.dispatch()
            return res.value()
        except:
            # NOTE: not entirely understood, but it seems this happens if FIFO is (suddenly?) empty
            return []

    def giant_dump(self, block=3000, subblock=255, format=True, align=True, rev_bits=False, daq=0):
        stream = []
        for i in range(block//subblock):
            stream += self.dump(block=subblock, format=format, daq=daq)
        stream += self.dump(block=block%subblock, format=format, daq=daq)
        if align:
            stream = self.align_stream(stream)
        if format:
            hex_dump = [ '{0:0{1}x}'.format(r,2) for r in stream ]
            if rev_bits: hex_dump = [ '{0:0{1}x}'.format(revbits(int(r, 16)),2) for r in hex_dump ]
            return hex_dump
        else:
            return [ self.make_word(c, reversed=(self.ETROC=='ETROC2')) for c in chunk(stream, n=5) if len(c)==5 ]
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

