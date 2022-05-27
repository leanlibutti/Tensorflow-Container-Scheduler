#!/bin/bash
export INTER_THREADS=$1
export INTRA_THREADS=$2

inter=$3
intra=$4
#inter=1
#intra=1

python3 $5 $inter $intra $6
