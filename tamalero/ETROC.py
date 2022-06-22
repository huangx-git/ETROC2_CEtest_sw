"""
For ETROC control
"""

class ETROC(write, read):

    def __init__(self, write, read):
        self.write = write
        self.read  = read

    def test_write(reg, data):
        print("Writing data %d to register %d"%(data, reg))
        self.write(reg, data)
        return None

    def test_read(reg):
        print("Reading data from register %d"%reg)
        return self.read(reg)
