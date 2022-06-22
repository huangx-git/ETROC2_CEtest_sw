"""
For ETROC control
"""

import ETROC_Emulator as etroc_em

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


    def select_CL(self, C):
        return

    def select_Rf(self, R):
        return

    def enable_discriminator(self, row):
        return

    def enable_QInj(self, pixel):
        return

    def select_QInj(self, ):
        return

    def DAC_Discri_power(self, pixels):
        return

    def select_HysV(self, V):
        return

    def bias_selection(I):
        return


    # =====================
    # == For vth s curve ==
    # =====================

    def set_vth(self, vth):
        self.test_write(0x1, vth)
        print("Vth set to %d."%vth)
        return

    def run(self, N):
        etroc_em.run(N)

    def run_results(self):
        return self.test_read(0x2)
