#!/bin/bash

for i in {10..20..1}
do
    echo "___________________________________ "$i
    ./autopilot.sh 1000 $i
    sleep 2m
done