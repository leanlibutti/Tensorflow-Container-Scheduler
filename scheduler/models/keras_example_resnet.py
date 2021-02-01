from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datetime import datetime
from packaging import version

import sys
import functools
import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow.python.keras import backend
from tensorflow.python.keras import layers

import numpy as np

## Agregado para el scheduler ##

from subprocess import Popen, PIPE, STDOUT

#################################

if len(sys.argv) != 4:
	print("cantidad de argumentos incorrectos")
	sys.exit(2)

inter=int(sys.argv[1])
intra=int(sys.argv[2])

## Agregado para el scheduler ##

pid_client=int(sys.argv[3])

#################################

tf.config.threading.set_inter_op_parallelism_threads(inter)
tf.config.threading.set_intra_op_parallelism_threads(intra)

print("TensorFlow version: ", tf.__version__)

BATCH_NORM_DECAY = 0.997
BATCH_NORM_EPSILON = 1e-5
L2_WEIGHT_DECAY = 2e-4


def identity_building_block(input_tensor,
                            kernel_size,
                            filters,
                            stage,
                            block,
                            training=None):
  """The identity block is the block that has no conv layer at shortcut.

  Arguments:
    input_tensor: input tensor
    kernel_size: default 3, the kernel size of
        middle conv layer at main path
    filters: list of integers, the filters of 3 conv layer at main path
    stage: integer, current stage label, used for generating layer names
    block: current block label, used for generating layer names
    training: Only used if training keras model with Estimator.  In other
      scenarios it is handled automatically.

  Returns:
    Output tensor for the block.
  """
  filters1, filters2 = filters
  if tf.keras.backend.image_data_format() == 'channels_last':
    bn_axis = 3
  else:
    bn_axis = 1
  conv_name_base = 'res' + str(stage) + block + '_branch'
  bn_name_base = 'bn' + str(stage) + block + '_branch'

  x = tf.keras.layers.Conv2D(filters1, kernel_size,
                             padding='same',
                             kernel_initializer='he_normal',
                             kernel_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             bias_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             name=conv_name_base + '2a')(input_tensor)
  x = tf.keras.layers.BatchNormalization(axis=bn_axis,
                                         name=bn_name_base + '2a',
                                         momentum=BATCH_NORM_DECAY,
                                         epsilon=BATCH_NORM_EPSILON)(
                                             x, training=training)
  x = tf.keras.layers.Activation('relu')(x)

  x = tf.keras.layers.Conv2D(filters2, kernel_size,
                             padding='same',
                             kernel_initializer='he_normal',
                             kernel_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             bias_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             name=conv_name_base + '2b')(x)
  x = tf.keras.layers.BatchNormalization(axis=bn_axis,
                                         name=bn_name_base + '2b',
                                         momentum=BATCH_NORM_DECAY,
                                         epsilon=BATCH_NORM_EPSILON)(
                                             x, training=training)

  x = tf.keras.layers.add([x, input_tensor])
  x = tf.keras.layers.Activation('relu')(x)
  return x


def conv_building_block(input_tensor,
                        kernel_size,
                        filters,
                        stage,
                        block,
                        strides=(2, 2),
                        training=None):
  """A block that has a conv layer at shortcut.

  Arguments:
    input_tensor: input tensor
    kernel_size: default 3, the kernel size of
        middle conv layer at main path
    filters: list of integers, the filters of 3 conv layer at main path
    stage: integer, current stage label, used for generating layer names
    block: current block label, used for generating layer names
    strides: Strides for the first conv layer in the block.
    training: Only used if training keras model with Estimator.  In other
      scenarios it is handled automatically.

  Returns:
    Output tensor for the block.

  Note that from stage 3,
  the first conv layer at main path is with strides=(2, 2)
  And the shortcut should have strides=(2, 2) as well
  """
  filters1, filters2 = filters
  if tf.keras.backend.image_data_format() == 'channels_last':
    bn_axis = 3
  else:
    bn_axis = 1
  conv_name_base = 'res' + str(stage) + block + '_branch'
  bn_name_base = 'bn' + str(stage) + block + '_branch'

  x = tf.keras.layers.Conv2D(filters1, kernel_size, strides=strides,
                             padding='same',
                             kernel_initializer='he_normal',
                             kernel_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             bias_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             name=conv_name_base + '2a')(input_tensor)
  x = tf.keras.layers.BatchNormalization(axis=bn_axis,
                                         name=bn_name_base + '2a',
                                         momentum=BATCH_NORM_DECAY,
                                         epsilon=BATCH_NORM_EPSILON)(
                                             x, training=training)
  x = tf.keras.layers.Activation('relu')(x)

  x = tf.keras.layers.Conv2D(filters2, kernel_size, padding='same',
                             kernel_initializer='he_normal',
                             kernel_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             bias_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             name=conv_name_base + '2b')(x)
  x = tf.keras.layers.BatchNormalization(axis=bn_axis,
                                         name=bn_name_base + '2b',
                                         momentum=BATCH_NORM_DECAY,
                                         epsilon=BATCH_NORM_EPSILON)(
                                             x, training=training)

  shortcut = tf.keras.layers.Conv2D(filters2, (1, 1), strides=strides,
                                    kernel_initializer='he_normal',
                                    kernel_regularizer=
                                    tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                                    bias_regularizer=
                                    tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                                    name=conv_name_base + '1')(input_tensor)
  shortcut = tf.keras.layers.BatchNormalization(
      axis=bn_axis, name=bn_name_base + '1',
      momentum=BATCH_NORM_DECAY, epsilon=BATCH_NORM_EPSILON)(
          shortcut, training=training)

  x = tf.keras.layers.add([x, shortcut])
  x = tf.keras.layers.Activation('relu')(x)
  return x


def resnet_block(input_tensor,
                 size,
                 kernel_size,
                 filters,
                 stage,
                 conv_strides=(2, 2),
                 training=None):
  """A block which applies conv followed by multiple identity blocks.

  Arguments:
    input_tensor: input tensor
    size: integer, number of constituent conv/identity building blocks.
    A conv block is applied once, followed by (size - 1) identity blocks.
    kernel_size: default 3, the kernel size of
        middle conv layer at main path
    filters: list of integers, the filters of 3 conv layer at main path
    stage: integer, current stage label, used for generating layer names
    conv_strides: Strides for the first conv layer in the block.
    training: Only used if training keras model with Estimator.  In other
      scenarios it is handled automatically.

  Returns:
    Output tensor after applying conv and identity blocks.
  """

  x = conv_building_block(input_tensor, kernel_size, filters, stage=stage,
                          strides=conv_strides, block='block_0',
                          training=training)
  for i in range(size - 1):
    x = identity_building_block(x, kernel_size, filters, stage=stage,
                                block='block_%d' % (i + 1), training=training)
  return x

def resnet(num_blocks, classes=10, training=None):
  """Instantiates the ResNet architecture.

  Arguments:
    num_blocks: integer, the number of conv/identity blocks in each block.
      The ResNet contains 3 blocks with each block containing one conv block
      followed by (layers_per_block - 1) number of idenity blocks. Each
      conv/idenity block has 2 convolutional layers. With the input
      convolutional layer and the pooling layer towards the end, this brings
      the total size of the network to (6*num_blocks + 2)
    classes: optional number of classes to classify images into
    training: Only used if training keras model with Estimator.  In other
    scenarios it is handled automatically.

  Returns:
    A Keras model instance.
  """

  input_shape = (32, 32, 3)
  img_input = layers.Input(shape=input_shape)

  if backend.image_data_format() == 'channels_first':
    x = layers.Lambda(lambda x: backend.permute_dimensions(x, (0, 3, 1, 2)),
                      name='transpose')(img_input)
    bn_axis = 1
  else:  # channel_last
    x = img_input
    bn_axis = 3

  x = tf.keras.layers.ZeroPadding2D(padding=(1, 1), name='conv1_pad')(x)
  x = tf.keras.layers.Conv2D(16, (3, 3),
                             strides=(1, 1),
                             padding='valid',
                             kernel_initializer='he_normal',
                             kernel_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             bias_regularizer=
                             tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                             name='conv1')(x)
  x = tf.keras.layers.BatchNormalization(axis=bn_axis, name='bn_conv1',
                                         momentum=BATCH_NORM_DECAY,
                                         epsilon=BATCH_NORM_EPSILON)(
                                             x, training=training)
  x = tf.keras.layers.Activation('relu')(x)

  x = resnet_block(x, size=num_blocks, kernel_size=3, filters=[16, 16],
                   stage=2, conv_strides=(1, 1), training=training)

  x = resnet_block(x, size=num_blocks, kernel_size=3, filters=[32, 32],
                   stage=3, conv_strides=(2, 2), training=training)

  x = resnet_block(x, size=num_blocks, kernel_size=3, filters=[64, 64],
                   stage=4, conv_strides=(2, 2), training=training)

  x = tf.keras.layers.GlobalAveragePooling2D(name='avg_pool')(x)
  x = tf.keras.layers.Dense(classes, activation='softmax',
                            kernel_initializer='he_normal',
                            kernel_regularizer=
                            tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                            bias_regularizer=
                            tf.keras.regularizers.l2(L2_WEIGHT_DECAY),
                            name='fc10')(x)

  inputs = img_input
  # Create model.
  model = tf.keras.models.Model(inputs, x, name='resnet56')

  return model


resnet20 = functools.partial(resnet, num_blocks=3)
resnet32 = functools.partial(resnet, num_blocks=5)
resnet56 = functools.partial(resnet, num_blocks=9)
resnet110 = functools.partial(resnet, num_blocks=18)

cifar_builder = tfds.builder('cifar10')
cifar_builder.download_and_prepare()

HEIGHT = 32
WIDTH = 32
NUM_CHANNELS = 3
NUM_CLASSES = 10
BATCH_SIZE = 128

def preprocess_data(record):
  image = record['image']
  label = record['label']
  
  # Resize the image to add four extra pixels on each side.
  image = tf.image.resize_with_crop_or_pad(
      image, HEIGHT + 8, WIDTH + 8)

  # Randomly crop a [HEIGHT, WIDTH] section of the image.
  image = tf.image.random_crop(image, [HEIGHT, WIDTH, NUM_CHANNELS])

  # Randomly flip the image horizontally.
  image = tf.image.random_flip_left_right(image)

  # Subtract off the mean and divide by the variance of the pixels.
  image = tf.image.per_image_standardization(image)
  
  label = tf.compat.v1.sparse_to_dense(label, (NUM_CLASSES,), 1)
  return image, label

train_data = cifar_builder.as_dataset(split=tfds.Split.TRAIN)
train_data = train_data.repeat()
train_data = train_data.map(
    lambda value: preprocess_data(value))
train_data = train_data.shuffle(1024)

train_data = train_data.batch(BATCH_SIZE)

model = resnet56(classes=NUM_CLASSES)

model.compile(optimizer='SGD',
              loss='categorical_crossentropy',
              metrics=['categorical_accuracy'])

log_dir="logs/profile/" + datetime.now().strftime("%Y%m%d-%H%M%S")

tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1, profile_batch = 3)


model.fit(train_data,
          steps_per_epoch=20,
          epochs=1, 
          callbacks=[tensorboard_callback])


## Agregado para el scheduler ##

command = "kill -10 " + pid_client

# Avisar al cliente del contenedor que se termina la ejecución del programa TF
process_command = Popen([command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
stdout, stderr = process_command.communicate()

#################################