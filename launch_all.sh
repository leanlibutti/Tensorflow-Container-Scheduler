ncpus=`cat /proc/cpuinfo | grep processor | wc -l`

export MIN_ENV_THREADS=$ncpus
export MAX_ENV_THREADS=$ncpus

python /data/tensorflow_examples/keras_example_tf2.py

exit
