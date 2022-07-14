#!/bin/bash
fichero='/root/tf_parallelism.txt'
echo 1 12 > $fichero
# Tiempo de inicio de ejecucion de prueba
inicio=`date +%s`
# Envio a ejecución primer algoritmo
python3 keras_example_resnet.py 1 12 10 &> execution1.txt & 
BACK_PID1=$!
echo "PID: $BACK_PID1" 
sleep 2
echo 1 6 > $fichero
sudo kill -12 $BACK_PID1
sleep 40
echo 1 12 > $fichero
sudo kill -12 $BACK_PID1
# Tiempo de finalizaci�n de la prueba
wait $BACK_PID1
fin=`date +%s`
let total=$fin-$inicio
echo "version elastica ha tardado: $total- segundos"

echo 1 6 > $fichero
inicio2=`date +%s`
python3 keras_example_resnet.py 1 6 10 &> execution2.txt & 
BACK_PID2=$!
echo "PID: $BACK_PID2" 
wait $BACK_PID2
fin2=`date +%s`
let total2=$fin2-$inicio2
echo "version original ha tardado: $total2- segundos"