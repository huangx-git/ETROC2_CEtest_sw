"""
For ETROC control
"""

from ETROC_Emulator import software_ETROC2

class ETROC():

    def __init__(self, write=None, read=None, usefake=False):
        self.usefake = usefake
        if usefake:
            self.fakeETROC = software_ETROC2()
        elif write == None or read == None:
            raise Exception("Pass in write&read functions for ETROC!")

    def write(self, reg, val):
        if self.usefake:
            self.fakeETROC.I2C_write(reg, val)
        return None

    def read(self, reg):
        if self.usefake:
            return self.fakeETROC.I2C_read(reg)
        return None


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
        self.write(0x1, vth)
        print("Vth set to %f."%vth)
        return

