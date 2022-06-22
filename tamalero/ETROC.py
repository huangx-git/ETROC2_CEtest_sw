"""
For ETROC control
"""

class ETROC():

    def __init__(self, write, read):
        self.write = write
        self.read  = read

    def test_write(self, reg, val):
        print("Writing val %d to register %d"%(val, reg))
        self.write(reg, val)
        return None

    def test_read(self, reg):
        print("Reading val from register %d"%reg)
        return self.read(reg)
