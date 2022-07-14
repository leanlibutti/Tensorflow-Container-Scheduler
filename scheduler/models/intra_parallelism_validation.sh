#!/bin/bash
# Ejecutar 3 veces variando el profile batch en keras para que tome un batch inicial, intermedio y final
fichero='/root/tf_parallelism.txt'
echo 1 16 > $fichero
# Tiempo de inicio de ejecucion de prueba
inicio=`date +%s`
# Envio a ejecución primer algoritmo
python3 keras_example_resnet.py 1 16 10 &> execution1.txt & 
BACK_PID1=$!
echo "PID: $BACK_PID1" 
sleep 10
# Disminuyo paralelismo inter a la mitad
echo 1 1 > $fichero
sudo kill -12 $BACK_PID1
sleep 60
# Incremento paralelismo inter a 16
echo 1 16 > $fichero
sudo kill -12 $BACK_PID1
#Espero finalizacion del algoritmo
wait $BACK_PID1
# Calculo tiempo (no es necesario para esta prueba)
fin=`date +%s`
let total=$fin-$inicio
echo "version elastica ha tardado: $total- segundos"