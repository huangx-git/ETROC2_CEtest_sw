#!/bin/bash

# 1) Number of runs
# 2) Bias voltage
# 3) Threshold offset
# 4) Number of events
# 5) The number of the PCb board, use "-" to separate boards id in multilayer setup
# 6) Wirebonded/Bump-bonded wb or bb
# 7) Beam energy
# 8) tracker
# 9) ETROC Power mode: i1,i2,i3,i4
# 9) Multilayer setup

# LOOP={10..12..1}
bias_V=$2 # V
offset=$3 # vth
n_events=$4
board_number=$5
bond=$6
energy=$7
isTrack=$8
powerMode=$9  # I1 (high) to I4 (low)
isMulti=${10}
run_number=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/next_run_number.txt`

if [ "$isTrack" = true ]
then
    echo "You are starting a telescope run. Have you entered the run number $run_number on telescope? And turn the beam OFF"
    read dummy
fi  
   
python3 telescope.py --kcu 192.168.0.10 --offset $3 --delay 32
python3 poke_board.py --kcu 192.168.0.10 --dark_mode

echo "Turn the beam on now!"

for i in $(seq 1 $1)
do
    merging_dir="../ETROC2_Test_Stand/ScopeHandler/ScopeData/LecroyMerged/"
    
    echo "___________________________________ "$i
    run_number=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/next_run_number.txt`
    echo "Run number: $run_number"
    python3 poke_board.py --kcu 192.168.0.10 --rb 2 --bitslip
    python3 poke_board.py --kcu 192.168.0.10 --rb 1 --bitslip
    ./autopilot.sh $n_events $offset
    temperature=$(python3 poke_board.py --kcu 192.168.0.10 --temperature)
    sleep 7s
    kcu=`cat ./running_ETROC_acquisition.txt`
    scope=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/running_acquisition.txt`
    conversion=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Conversion/ongoing_conversion.txt`
    merging=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Merging/ongoing_merging.txt`
    echo $kcu
    echo $scope
    echo $conversion
    echo $merging

    while [ $kcu == "True" ] || [ $scope == "True" ] || [ $conversion == "True" ] || [ $merging == "True" ]; do
        echo "Waiting..."
        sleep 1s
        kcu=`cat ./running_ETROC_acquisition.txt`
        scope=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/running_acquisition.txt`
        conversion=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Conversion/ongoing_conversion.txt`
        merging=`cat ../ETROC2_Test_Stand/ScopeHandler/Lecroy/Merging/ongoing_merging.txt`
        echo $kcu
        echo $scope
        echo $conversion
        echo $merging
    done

    test_successful=`test "$merging_dir/run_$run_number.root"`

    printf "$run_number,$bias_V,$offset,$n_events,$board_number,$bond,$energy,`date -u`,$isTrack,$powerMode,$temperature, $isMulti \n">>./run_log_DESY_March2024.csv

done
