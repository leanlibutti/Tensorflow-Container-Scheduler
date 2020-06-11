#!/bin/bash
export MIN_ENV_THREADS=$1
export MAX_ENV_THREADS=$2
export ITERATION_DOWN=$3
export ITERATION_UP=$4

inter=1
intra=1

for value in {1..6}
do
	for value2 in {1..6}
	do
		python3 keras_example_VGG.py $inter $intra
		let intra=$intra*2
	done
	let intra=1
	let inter=$inter*2
done

