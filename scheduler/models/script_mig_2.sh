#!/bin/bash
inicio_ns1=`date +%s%N`
inicio1=`date +%s`

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64

# Reset MIG configuration (delete old MIG instances)
sudo nvidia-smi --gpu-reset

# Create two MIGs with 28 SMs and 12 Gb each
sudo nvidia-smi mig -cgi 5,5 -C

#                 #MIG 2g.12gb                                       #MIG 2g.12gb                 
mig_devices=(MIG-ce853f1c-503b-5880-9e38-3bcdabec90c5 MIG-432dcd12-c4e2-5f68-88a5-c6910494d130) # only found in GPU A30
inc=1
val=0
# Lanzar todas las instancias GPUS con el algoritmo de Keras
for i in {0..1}
do 
    export CUDA_VISIBLE_DEVICES=${mig_devices[$i]}
    for j in {0..1}
    do
        # python3 keras_example_gpu.py 1 4 $val &> execution$val.txt & 
        python3 convnets/main.py --nets=ResNet50 --epochs=5 &> execution$val.txt &
        pids[${val}]=$!
        val=`expr $val + $inc`
    done
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