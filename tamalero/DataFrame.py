#!/usr/bin/env python3

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class DataFrame:
    def __init__(self, version='ETROC1'):
        with open(f_in, 'r') as f:
            self.format = load(f, Loader=Loader)[version]

    def read(self, val):
        for types in self.format['identifiers']:
            self.format


if __name__ == '__main__':

    test = [
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
