# Copyright 2018 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
#
# THIS IS A GENERATED DOCKERFILE.
#
# This file was assembled from multiple pieces, whose use is documented
# throughout. Please refer to the TensorFlow dockerfiles documentation
# for more information.

ARG UBUNTU_VERSION=20.04
FROM ubuntu:${UBUNTU_VERSION}
ADD ../ /scheduler_src
ARG DEBIAN_FRONTEND=noninteractive    
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libcurl3-dev \
    libfreetype6-dev \
    libhdf5-serial-dev \
    libzmq3-dev \
    pkg-config \
    rsync \
    software-properties-common \
	sudo \
        unzip \
        zip \
        zlib1g-dev \
        openjdk-8-jdk \
        openjdk-8-jre-headless \
        iproute2 \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


ENV CI_BUILD_PYTHON python

# CACHE_STOP is used to rerun future commands, otherwise cloning tensorflow will be cached and will not pull the most recent version
ARG CACHE_STOP=1
# Check out TensorFlow source code if --build-arg CHECKOUT_TF_SRC=1
ARG CHECKOUT_TF_SRC=0

RUN chmod a+w /etc/passwd /etc/group
#RUN test "${CHECKOUT_TF_SRC}" -eq 1 && git clone https://github.com/tensorflow/tensorflow.git /tensorflow_src || true

ARG USE_PYTHON_3_NOT_2=1
ARG _PY_SUFFIX=${USE_PYTHON_3_NOT_2:+3}
ARG PYTHON=python3
ARG PIP=pip${_PY_SUFFIX}
# See http://bugs.python.org/issue19846
ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y \
    ${PYTHON} \
    ${PYTHON}-pip

# RUN ${PIP} --no-cache-dir install --upgrade \
#     pip \
#     setuptools

# Some TF tools expect a "python" binary
RUN ln -s $(which ${PYTHON}) /usr/local/bin/python 
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    wget \
    openjdk-8-jdk \
    ${PYTHON}-dev \
    virtualenv \
    swig

RUN ${PIP} --no-cache-dir install \
    Pillow \
    h5py \
    keras_applications \
    keras_preprocessing \
    matplotlib \
    mock \
    numpy \
    scipy \
    sklearn \
    pandas \
    future \
    portpicker \
    && test "${USE_PYTHON_3_NOT_2}" -eq 1 && true || ${PIP} --no-cache-dir install \
    enum34

# Install bazel
ARG BAZEL_VERSION=3.7.0
RUN mkdir /bazel && \
    wget -O /bazel/installer.sh "https://github.com/bazelbuild/bazel/releases/download/${BAZEL_VERSION}/bazel-${BAZEL_VERSION}-installer-linux-x86_64.sh" && \
    wget -O /bazel/LICENSE.txt "https://raw.githubusercontent.com/bazelbuild/bazel/master/LICENSE" && \
    chmod +x /bazel/installer.sh && \
    /bazel/installer.sh && \
    rm -f /bazel/installer.sh

#RUN cd /tensorflow_src && \
#    bazel build //tensorflow/tools/pip_package:build_pip_package && \
#    rm tensorflow/core/common_runtime/executor.cc && \ 
#    rm tensorflow/core/platform/threadpool.* && \
#    cp Modify_Archives/core/common_runtime/executor.cc tensorflow/core/common_runtime && \
#    cp Modify_Archives/core/platform/* tensorflow/core/platform && \
#    cp Modify_Archives/NonBlockingThreadPool.h bazel-out/k8-opt/bin/tensorflow/tools/pip_package/build_pip_package.runfiles/eigen_archive/unsupported/Eigen/CXX11/src/ThreadPool/NonBlockingThreadPool.h && \
#    cp Modify_Archives/ThreadPoolInterface.h bazel-out/k8-opt/bin/tensorflow/tools/pip_package/build_pip_package.runfiles/eigen_archive/unsupported/Eigen/CXX11/src/ThreadPool/ThreadPoolInterface.h && \
#    bazel build //tensorflow/tools/pip_package:build_pip_package && \
#    ./bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg && \
#    pip install /tmp/tensorflow_pkg/tensorflow-2.0.0-cp36-cp36m-linux_x86_64.whl
#    cd ..

RUN pip3 --version
RUN cd /scheduler_src && \
    pip3 install tensorflow-2.4.0-cp38-cp38-linux_x86_64.whl
RUN pip3 install packaging && \
    pip3 install tensorflow-datasets && \
    pip3 install tensorboard && \
    apt-get install htop && \ 
    apt-get install nano

RUN pip3 install plotly && \
    pip3 install pandas

RUN apt-get update 
RUN apt install docker.io -y
RUN docker --version
#TF Warmup
RUN echo '1 1' > /root/tf_parallelism.txt
# RUN python3 /scheduler_src/models/keras_example_resnet_warmup.py 1 1 1
RUN python3 /scheduler_src/models/keras_example_VGG_warmup.py 1 1 1
# Insert Tensorflow program and parameters
# ENTRYPOINT python3 /home/Scheduler/Client/client.py keras_example_resnet
ENTRYPOINT python3 /home/Scheduler/Client/client.py keras_example_VGG

