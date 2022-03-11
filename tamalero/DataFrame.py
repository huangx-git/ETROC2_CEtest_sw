#!/usr/bin/env python3
import os

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class DataFrame:
    def __init__(self, version='ETROC1'):
        with open(os.path.expandvars('$TAMALERO_BASE/configs/dataformat.yaml'), 'r') as f:
            self.format = load(f, Loader=Loader)[version]

    def read(self, val):
        data_type = None
        for id in self.format['identifiers']:
            if self.format['identifiers'][id]['frame'] == (val & self.format['identifiers'][id]['mask']):
                data_type = id
        #print (val, data_type)
        if data_type == 'filler': print(val)
        if data_type == None:
            print ("Found data of type None:", val)
        res = {}
        for d in self.format['data'][data_type]:
            res[d] = (val & self.format['data'][data_type][d]['mask']) >> self.format['data'][data_type][d]['shift']
        #print (res)
        return data_type, res

if __name__ == '__main__':

    test_words = [
        0xcaaaaaaaaa,
        0xcaaaaaaaaa,
        0x35555559a7,
        0x40e691e374,
        0x6bc9425dc9,
        0x9555555404,
        0xcaaaaaaaaa,
        0x355555519b,
        0x4d02689a90,
        0x76b1f4de3a,
        ]

    df = DataFrame('ETROC1')
    for word in test_words:
        df.read(word)
