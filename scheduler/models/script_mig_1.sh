#!/bin/bash
inicio_ns1=`date +%s%N`
inicio1=`date +%s`

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/extras/CUPTI/lib64

# Reset MIG configuration (delete old MIG instances)
sudo nvidia-smi --gpu-reset

# Create one MIG with 56 SMs and 24 Gb each
sudo nvidia-smi mig -cgi 0 -C

                #MIG 4g.24gb                                                   
mig_device=(MIG-6cacf921-7a14-542f-babb-cacfee65bca0)

# Lanzar todas las instancias GPUS con el algoritmo de Keras
export CUDA_VISIBLE_DEVICES=${mig_device[$i]}
for j in {0..3}
    do
        python3 convnets/main.py --nets=ResNet50 --epochs=5 &> execution$j.txt & 
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