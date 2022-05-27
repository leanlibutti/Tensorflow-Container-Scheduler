from __future__ import absolute_import, division, print_function
from tqdm import tqdm
from numpy.random import randn

import sys 
import pathlib
import random
import matplotlib.pyplot as plt
 
import tensorflow as tf
import numpy as np
 
from matplotlib.image import imread
from tensorflow.keras.preprocessing import image

from datetime import datetime

## Agregado para el scheduler ##

from subprocess import Popen, PIPE, STDOUT

#################################
 
#tf.enable_eager_execution()
 
if(len(sys.argv)!= 4):
	print("cantidad de argumentos incorrecto")
	sys.exit(2)

inter= int(sys.argv[1])
intra= int(sys.argv[2])

## Agregado para el scheduler ##

pid_client=int(sys.argv[3])

#################################

print("TF inter: ", tf.config.threading.get_inter_op_parallelism_threads())
print("TF intra: ", tf.config.threading.get_inter_op_parallelism_threads())

tf.config.threading.set_inter_op_parallelism_threads(inter)
tf.config.threading.set_intra_op_parallelism_threads(intra)

AUTOTUNE = tf.data.experimental.AUTOTUNE
 
data_dir = tf.keras.utils.get_file('flower_photos','https://storage.googleapis.com/download.tensorflow.org/example_images/flower_photos.tgz', untar=True)
data_dir = pathlib.Path(data_dir)
 
label_names={'daisy': 0, 'dandelion': 1, 'roses': 2, 'sunflowers': 3, 'tulips': 4}
label_key=['daisy','dandelion','roses','sunflowers','tulips']

all_images = list(data_dir.glob('*/*'))
all_images = [str(path) for path in all_images]
random.shuffle(all_images)
 
all_labels=[label_names[pathlib.Path(path).parent.name] for path in all_images]
 
data_size=len(all_images)
 
train_test_split=(int)(data_size*0.2)
 
x_train=all_images[train_test_split:]
x_test=all_images[:train_test_split]
 
y_train=all_labels[train_test_split:]
y_test=all_labels[:train_test_split]
 
IMG_SIZE=160
 
BATCH_SIZE = 16
 
def _parse_data(x,y):
  image = tf.io.read_file(x)
  image = tf.image.decode_jpeg(image, channels=3)
  image = tf.cast(image, tf.float32)
  image = (image/127.5) - 1
  image = tf.image.resize(image, (IMG_SIZE, IMG_SIZE))
 
  return image,y
 
def _input_fn(x,y):
  ds=tf.data.Dataset.from_tensor_slices((x,y))
  ds=ds.map(_parse_data)
  ds=ds.shuffle(buffer_size=data_size)
  
  
  ds = ds.repeat()
  
  ds = ds.batch(BATCH_SIZE)
  
  ds = ds.prefetch(buffer_size=AUTOTUNE)
  
  return ds
  
train_ds=_input_fn(x_train,y_train)
validation_ds=_input_fn(x_test,y_test)

IMG_SHAPE = (IMG_SIZE, IMG_SIZE, 3)
VGG16_MODEL=tf.keras.applications.VGG16(input_shape=IMG_SHAPE,
                                               include_top=False,
                                               weights='imagenet')

VGG16_MODEL.trainable=False
global_average_layer = tf.keras.layers.GlobalAveragePooling2D()
prediction_layer = tf.keras.layers.Dense(len(label_names),activation='softmax')

model = tf.keras.Sequential([
  VGG16_MODEL,
  global_average_layer,
  prediction_layer
])

model.compile(optimizer=tf.optimizers.Adam(), 
              loss=tf.keras.losses.sparse_categorical_crossentropy,
              metrics=["accuracy"])

log_dir="logs/profile/" + datetime.now().strftime("%Y%m%d-%H%M%S")+ "-VGG"

tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1, profile_batch = 3)

history = model.fit(train_ds,
                    epochs=1, 
                    steps_per_epoch=100)
                    #callbacks=[tensorboard_callback])

print("Finish TF program")

## Agregado para el scheduler ##

command = "kill -10 " + str(pid_client)

# Avisar al cliente del contenedor que se termina la ejecución del programa TF
#process_command = Popen([command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
#stdout, stderr = process_command.communicate()
tf_execute = Popen(command, shell=True)
print("Send Signal")
#################################