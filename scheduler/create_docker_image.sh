# $1: name of image, for ex. tf_scheduler
# $2: docker image, for ex. tensorflow-program.Dockerfile

docker build -t $1 -f  $2 .
