#!/bin/bash
inicio_ns1=`date +%s%N`
inicio1=`date +%s`
# Reset MIG configuration (delete old MIG instances)
sudo nvidia-smi --gpu-reset

# Create four MIGs with 14 SMs and 6 Gb each
sudo nvidia-smi mig -cgi 14,14,14,14 -C

                       # MIG 1g.6gb                                   #MIG 1g.6gb                             #MIG 1g.6gb                              #MIG 1g.6gb 
mig_devices=(MIG-075602d5-888a-5f85-bf04-e6f9b9c3e0a9 MIG-2a9103c2-42aa-5b32-a00f-a22d442119ef MIG-ba9efa5f-b4f3-525d-95a9-c94fa6fabd60 MIG-085a4e0c-d7b9-5fe6-b98a-13b4e58bdda1)
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64
# Lanzar todas las instancias GPUS con el algoritmo de Keras
for i in {0..3}
do
    export CUDA_VISIBLE_DEVICES=${mig_devices[$i]}
    # python3 keras_example_gpu.py 1 4 $i &> execution$i.txt & 
    python3 convnets/main.py --nets=ResNet50 --epochs=5 &> execution$i.txt &
    pids[${j}]=$!
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