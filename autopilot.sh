next_file_index="/home/etl/Test_Stand/ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/next_run_number.txt"
index=`cat $next_file_index`
echo $index

ipython3 telescope.py -- --kcu 192.168.0.10 --offset $2
echo -n "True" > running_ETROC_acquisition.txt
(python3 daq.py --l1a_rate 0 --ext_l1a --kcu 192.168.0.10 --rb 0 --run $index --lock "/home/etl/Test_Stand/ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/running_acquisition.txt") &
(sleep 15
python3 /home/etl/Test_Stand/ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/acquisition_wrapper.py $1)
python3 data_dumper.py --input ${index}_rb0
python3 root_dumper.py --input ${index}_rb0
echo -n "False" > running_ETROC_acquisition.txt
echo -n "True" > merging.txt
echo -n "True" > /home/etl/Test_Stand/ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/merging.txt
