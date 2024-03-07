next_file_index="$TAMALERO_BASE/../ScopeHandler/Lecroy/Acquisition/next_run_number.txt"
index=`cat $next_file_index`
echo $index

ipython3 fnal_laser_test.py -- --kcu 192.168.0.10 --hard_reset --offset $2
echo -n "True" > running_ETROC_acquisition.txt
(python3 daq.py --l1a_rate 0 --ext_l1a --kcu 192.168.0.10 --run $index --lock "$TAMALERO_BASE/../ScopeHandler/Lecroy/Acquisition/running_acquitision.txt") &
(sleep 15
python3 $TAMALERO_BASE/../ScopeHandler/Lecroy/Acquisition/acquisition_wrapper.py $1)
python3 data_dumper.py --input $index
python3 root_dumper.py --input $index
echo -n "False" > running_ETROC_acquisition.txt
echo -n "True" > merging.txt
echo -n "True" > $TAMALERO_BASE/../ScopeHandler/Lecroy/Acquisition/merging.txt
