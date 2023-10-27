import os
import traceback
from datetime import datetime
import argparse

parser = argparse.ArgumentParser()
#parser.add_argument('--config', '-c', action = 'store', default = '')
parser.add_argument('--outdir', '-o',  action = 'store', default = 'results/')
parser.add_argument('--pixels', action = 'store', default = '4,3', nargs = '+')
parser.add_argument('--charges', '-q', action = 'store', nargs = '*', default = [], type = int)
parser.add_argument('--comp_loc', action = 'store', default = '')
parser.add_argument('--skip_complete', action = 'store_true')
parser.add_argument('--kcu', action = 'store', default = '192.168.0.11')
parser.add_argument('--skip_sanity_checks', action = 'store_true')
parser.add_argument('--vth_axis', action = 'store', nargs = '*', default = [])
parser.add_argument('--nl1a', action = 'store', default = '3200')
args = parser.parse_args()

coords = [[int(c.split(',')[0]), int(c.split(',')[1])] for c in args.pixels]
if args.kcu == '192.168.0.10':
    configuration = 'modulev0'
if args.kcu == '192.168.0.11':
    configuration = 'modulev0b'
if args.skip_sanity_checks:
    skip_sanity_checks = '--skip_sanity_checks'
else:
    skip_sanity_checks = ''

if len(args.vth_axis) > 0:
    vth_axis = '--vth_axis ' + ' '.join(args.vth_axis)
else:
    vth_axis = ''


for coord in coords:
    i = coord[0]
    j = coord[1]
    pix = f'r{i}c{j}'
    done = [os.path.exists(args.outdir +  f'/{pix}/Qinj_scan_L1A_504_{q}.dat') for q in args.charges]
    print(done)
    try:
        print(os.listdir(args.outdir))
    except:
        print('Given outdir not found.')
    if args.skip_complete:
        if not any(done):
            print(f'No existing files found for Row {i} Col {j} for any given charges at this output location. Testing all charges')
        elif all(done):
            print(f'Files found for Row {i} Col {j} for all charges given. Skipping these charges')
        else:
            print(f'Found files for Row {i} Col {j} for ', ''.join([f'{q}, ' for q in args.charges[done]])[:-2])
            print('Will run on ', ''.join([f'{q}, ' for q in args.charges[~done]]))
    else:
        if not any(done):
            print(f'No existing files found for Row {i} Col {j} for any given charges at this output location')
        elif all(done):
            print(f'Files found for Row {i} Col {j} for all charges given. Overwriting')
        else:
            print(f'Found files for Row {i} Col {j} for ', ''.join([f'{q}, ' for q in args.charges[done]]))
            print('Will run on all given charges')

    if len(args.charges) > 0:
        charges = '--charges ' + ' '.join([str(q) for q in args.charges])
        try:
            os.makedirs(args.outdir + f'/{pix}/', exist_ok = True)
            print(f'Generating data for Row {i} Col {j} at {datetime.now().ctime()}')
            command = f'python test_ETROC.py --configuration {configuration} --kcu {args.kcu} --test_chip --qinj_vth_scan --nl1a {args.nl1a}  {skip_sanity_checks} {charges} {vth_axis} --row {i} --col {j}  --outdir {args.outdir}/{pix}/  > {args.outdir}/{pix}/output.txt 2> {args.outdir}/{pix}/errors.txt'
            print(command)
            os.system(command)
        except:
            traceback.print_exc()
            print()

