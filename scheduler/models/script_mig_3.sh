#!/bin/bash
inicio_ns1=`date +%s%N`
inicio1=`date +%s`
# Reset MIG configuration (delete old MIG instances)
sudo nvidia-smi --gpu-reset

# Create two MIGs with 14 SMs and 6 Gb and one MIG with 28 SMs and 12 Gb
sudo nvidia-smi mig -cgi 5,14,14 -C

                #MIG 2g.12gb                                       #MIG 1g.6gb                             #MIG 1g.6gb 
mig_devices=(MIG-ce853f1c-503b-5880-9e38-3bcdabec90c5 MIG-ba9efa5f-b4f3-525d-95a9-c94fa6fabd60 MIG-085a4e0c-d7b9-5fe6-b98a-13b4e58bdda1)

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64
inc=1
val=0
# Lanzar todas las instancias GPUS con el algoritmo de Keras
for i in {0..2}
do
    export CUDA_VISIBLE_DEVICES=${mig_devices[$i]}
    if [ $i -eq 0 ]
    then
        for j in {0..1}
        do
            python3 convnets/main.py --nets=ResNet50 --epochs=5 &> execution$val.txt &
            # python3 keras_example_gpu.py 1 4 $val &> execution$val.txt & 
            pids[${val}]=$!
            val=`expr $val + $inc`
        done
    else
        python3 convnets/main.py --nets=ResNet50 --epochs=5 &> execution$val.txt &
        # python3 keras_example_gpu.py 1 4 $val &> execution$val.txt & 
        pids[${val}]=$!
        val=`expr $val + $inc`
    fi
done
# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
fin_ns1=`date +%s%N`
fin1=`date +%s`
let total_ns1=$fin_ns1-$inicio_ns1
let total1=$fin1-$inicio1
echo "ha tardado: -$total_ns1- nanosegudos, -$total1- segundos"