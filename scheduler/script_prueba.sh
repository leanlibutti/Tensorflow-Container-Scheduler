#!/bin/bash
threads=12
python3 models/keras_example_resnet.py 1 12 20 &
sleep 30
for i in {1..12}
do
    echo 1 $threads > /home/tf_parallelism.txt
    pid_processes=$!
    echo $pid_processes
    kill -12 $pid_processes
    sleep 5 # Densenet
    let threads=$threads-1
done
