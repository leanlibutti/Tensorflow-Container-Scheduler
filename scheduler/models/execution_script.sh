#!/bin/bash
#$1: paralelismo inter
#$2: paralelismo intra 
#$3: algoritmo
#$4: name of log file
fichero='/root/tf_parallelism.txt'
echo $1 $2 > $fichero
# Tiempo de inicio de ejecucion de prueba
inicio=`date +%s`
python3 $3 $1 $2 10 > $4 &
BACK_PID1=$!
wait $BACK_PID1
fin=`date +%s`
let total=$fin-$inicio
echo "ha tardado: $total- segundos"
