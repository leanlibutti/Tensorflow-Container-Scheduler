#!/bin/bash
inicio_ns1=`date +%s%N`
inicio1=`date +%s`
intra=4
fichero='/root/tf_parallelism.txt'
# Envio a ejecución primer algoritmo
python3 keras_example_resnet.py 2 4 10 &> execution1.txt & 
BACK_PID1=$!
sleep 60
for i in {1..3} # Decremento el paralelismo intra a 1
    do
        let intra=$intra-1
        echo 2 $intra > $fichero
        sudo kill -12 $BACK_PID1
        sleep 2
    done
sleep 240 # Espero para enviar la segunda petición (aproximadamente a la mitad de ejecución del primer algoritmo)
inicio_ns2=`date +%s%N`
inicio2=`date +%s`
python3 keras_example_resnet.py 2 4 10 &> execution2.txt & # Envio a ejecución el segundo algoritmo
BACK_PID2=$!
sleep 60
intra=4
for i in {1..3} # Decremento el paralelismo intra a 1
    do
        let intra=$intra-1
        echo 2 $intra > $fichero
        sudo kill -12 $BACK_PID2
        sleep 2
    done

wait $BACK_PID1 # Espero a que termine el primer algoritmo
fin_ns1=`date +%s%N`
fin1=`date +%s`
let total_ns1=$fin_ns1-$inicio_ns1
let total1=$fin1-$inicio1
echo "ha tardado: -$total_ns1- nanosegudos, -$total1- segundos"

#Envio aumento de paralelismo al segundo algoritmo
echo 2 4 > $fichero
sudo kill -12 $BACK_PID2
wait $BACK_PID2 # Espero a que termine el segundo algoritmo
fin_ns2=`date +%s%N`
fin2=`date +%s`
let total_ns2=$fin_ns2-$inicio_ns2
let total2=$fin2-$inicio2
echo "ha tardado: -$total_ns2- nanosegudos, -$total2- segundos"
