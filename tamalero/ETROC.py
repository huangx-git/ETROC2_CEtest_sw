"""
For ETROC control
"""
import numpy as np

class ETROC():

    def __init__(self, write, read):
        self.write = write
        self.read  = read

    def test_write(self, reg, val):
        print("Writing to register %d"%reg)
        self.write(reg, val)
        return None

    def test_read(self, reg):
        return self.read(reg)

    def set_vth(self, vth):
        self.test_write(0x1, vth)
        print("Vth set to %d."%vth)
        return

    def runpixel(self, N):
        acc_num = 0
        vth = self.test_read(0x1)
        for i in range(N):
            val = np.random.normal(198, 0.5)
            if val > vth :
                acc_num += 1
        return acc_num

    def run(self, N):
        maxpixel = 16
        alldata = [0 for x in range(maxpixel)]
        for pixel in range(maxpixel):
            alldata[pixel] = self.runpixel(N)
        self.test_write(0x2, alldata)

    def run_results(self):
        return self.test_read(0x2)
