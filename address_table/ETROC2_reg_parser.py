import csv
import re
import yaml
import numpy as np

class hexint(int): pass
def hexint_presenter(dumper, data):
    return dumper.represent_int(hex(data))
yaml.add_representer(hexint, hexint_presenter)

def rangetomask(start, end):
  start = int(start)
  end = int(end)
  mask = 1
  for i in range(end-start):
    mask = (mask<<1) + 1
  return "0x{:02X}".format(mask<<start)

def pix2rc(pix):
  return pix%16, int(np.floor(pix/16))

with open('etroc2_regs.csv', newline='') as csvfile:
  f = csv.reader(csvfile, delimiter=',')
  dumpdata = {}
  for row in f:
    name = re.split('\<|\[', row[0])[0]
    default = hex(int(re.split('b',row[2])[1],2))
    adr = list(filter(None, re.split('\], |\],| \[|\[|\]|:',row[1]))) 
    if len(adr) == 2 :
      regadr = adr[0]
      shift = adr[1]
      mask = rangetomask(adr[1], adr[1])
    elif len(adr) == 3:
      regadr = adr[0]
      shift = adr[2]
      mask = rangetomask(adr[2], adr[1])
    elif len(adr) == 6:
      regadr = [adr[0], adr[3]]
      shift = [adr[2], adr[5]]
      mask = [rangetomask(adr[2], adr[1]),rangetomask(adr[5], adr[4])]
    elif len(adr) == 5:
      if len(adr[2]) > 2: # 2-3 case
        regadr = [adr[0], adr[2]]
        shift = [adr[1], adr[4]]
        mask = [rangetomask(adr[1], adr[1]),rangetomask(adr[4], adr[3])]
      else: # 3-2 case
        regadr = [adr[0], adr[3]]
        shift = [adr[2], adr[4]]
        mask = [rangetomask(adr[2], adr[1]),rangetomask(adr[4], adr[4])]
    else:
      print('Something is  wrong!', name)
   

    if isinstance(regadr, list):
      dumpdata[name] = {
        'shift': [int(s) for s in shift],
        'mask': [hexint(int(m, 16)) for m in mask],
        'default': hexint(int(default, 16)),
        'regadr': {}
      }
      for pix in range(256):
        r, c = pix2rc(pix)
        dumpdata[name]['regadr'][pix] = [s.replace('<Rn>', str(r)).replace('<Cn>', str(c)) for s in regadr]
    else:
      dumpdata[name] = {
        'shift': int(shift),
        'mask': hexint(int(mask, 16)),
        'default': hexint(int(default, 16)),
        'regadr': {}
      }
      for pix in range(256):
        r, c = pix2rc(pix)
        dumpdata[name]['regadr'][pix] = regadr.replace('<Rn>', str(r)).replace('<Cn>', str(c))
 

with open(r'ETROC2.yaml', 'w') as file:
    documents = yaml.dump(dumpdata, file)


dumpregs = {}
with open('etroc2_inpixel.csv', newline='') as csvfile:
  f = csv.reader(csvfile, delimiter=',')
  for row in f:
    for pix in range(256):
      r, c = pix2rc(pix)
      regname = re.split('/',row[0])[0].replace('<Rn>', str(r)).replace('<Cn>', str(c))
      dumpregs[regname] = row[1]
with open(r'ETROC2_inpixel.yaml', 'w') as file:
    documents = yaml.dump(dumpregs, file)
