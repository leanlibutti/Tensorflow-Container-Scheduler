from __future__ import absolute_import, division, print_function, unicode_literals
import tensorflow as tf
import tensorflow_datasets as tfds
import sys
from datetime import datetime

if len(sys.argv) != 3:
    	print("cantidad de argumentos incorrectos")
	sys.exit(2)

inter=int(sys.argv[1])
intra=int(sys.argv[2])

tf.config.threading.set_inter_op_parallelism_threads(inter)
tf.config.threading.set_intra_op_parallelism_threads(intra)

tf.compat.v1.disable_eager_execution()

datasets, info = tfds.load(name='mnist', with_info=True, as_supervised=True)
mnist_train, mnist_test = datasets['train'], datasets['test']

BUFFER_SIZE = 10 # Use a much larger value for real code.
BATCH_SIZE = 64
NUM_EPOCHS = 5
STEPS_PER_EPOCH = 5

def scale(image, label):
  image = tf.cast(image, tf.float32)
  image /= 255

  return image, label

train_data = mnist_train.map(scale).shuffle(BUFFER_SIZE).batch(BATCH_SIZE)
test_data = mnist_test.map(scale).batch(BATCH_SIZE)

train_data = train_data.take(STEPS_PER_EPOCH)
test_data = test_data.take(STEPS_PER_EPOCH)

model = tf.keras.Sequential([
    tf.keras.layers.Conv2D(32, 3, activation='relu',
                           kernel_regularizer=tf.keras.regularizers.l2(0.02),
                           input_shape=(28, 28, 1)),
    tf.keras.layers.MaxPooling2D(),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dropout(0.1),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.Dense(10, activation='softmax')
])

# Model is the full model w/o custom layers
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

log_dir="logs/profile/" + datetime.now().strftime("%Y%m%d-%H%M%S")

tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1, profile_batch = 3)

model.fit(train_data, epochs=NUM_EPOCHS, callbacks=[tensorboard_callback])
#loss, acc = model.evaluate(test_data)
#print("Loss {}, Accuracy {}".format(loss, acc))

