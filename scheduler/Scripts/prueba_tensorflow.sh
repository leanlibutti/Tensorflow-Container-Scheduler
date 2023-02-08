#!/bin/bash
threads=4
for i in {1..5}
do
    echo 1 16 > /root/tf_parallelism.txt
    python3 models/keras_example_resnet.py 1 16 20 &
    pid_processes=$!
    sleep 10
    echo $pid_processes
    echo 1 $threads > /home/tf_parallelism.txt
    kill -12 $pid_processes
    wait $pid_processes
    # let threads=$threads-1
done
