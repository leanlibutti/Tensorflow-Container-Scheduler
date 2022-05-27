#!/bin/bash
fichero='/root/tf_parallelism.txt'
echo 1 7 > $fichero
# Tiempo de inicio de ejecucion de prueba
inicio=`date +%s`
# Envio a ejecución primer algoritmo
python3 keras_example_resnet.py 1 7 10
# Tiempo de finalizaci�n de la prueba
fin=`date +%s`
let total=$fin-$inicio
echo "ha tardado: $total- segundos"


