from subprocess import Popen, PIPE, STDOUT
container_name= 'instance'
cant_containers=128

for value in range(0,cant_containers):
    docker_command= 'docker run -dit --cpus=8 --name '+ container_name + str(value) + ' --volume $HOME/scheduler:/home/Scheduler test_tf_massive'
    print(docker_command)
    # Ejecutar comando (con os.p)
    # Los primeros 12 caracteres de stdout son el Execution container request:container ID
    process_command = Popen([docker_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    stdout, stderr = process_command.communicate()
    if (stderr):
        print(stderr)
    else:
        print(stdout)
