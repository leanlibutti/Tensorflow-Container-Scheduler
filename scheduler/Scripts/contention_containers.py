from subprocess import Popen, PIPE, STDOUT
import time
import csv
container_name= 'tf_oversubscription_original'
# container_name= 'tf_oversubscription'
model_name= 'keras_example_resnet.py'
interparalelismo=1
f = open('times_contention.csv', 'a')
writer = csv.writer(f)
header = ['Cores_Per_C', 'Containers', 'Time']
# write the header
writer.writerow(header)
f.close()
base_logdir= 'logs_contention'
create_logdir= 'mkdir ' + base_logdir
process_command = Popen([create_logdir], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
stdout, stderr = process_command.communicate()
for cores_per_container in [1,2,4,8,16,32,48,64]:
    create_logdir_cores= 'mkdir ' + base_logdir +'/logs_contention_' + str(cores_per_container) 
    process_command = Popen([create_logdir_cores], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    stdout, stderr = process_command.communicate()
    cant_containers= int(256/cores_per_container)
    # for launch_containers in range(1,17):
    for launch_containers in [1,2,4,8,16,32,48,64,80]:
        list_containers=[]
        for num_container in range(launch_containers):  
            docker_command= 'docker run -dit --cpus=' + str(cores_per_container) + ' --name cores_'+  str(cores_per_container) + '_container_' + str(num_container)  + ' --volume=$HOME/scheduler:/home/scheduler ' + container_name + ' ' + str(interparalelismo) + ' ' + str(cores_per_container) + ' /home/scheduler/models/' + model_name + ' /home/scheduler/Scripts/' + base_logdir +  '/logs_contention_' + str(cores_per_container) + '/execution_' + str(num_container) + '.txt'
            print(docker_command)
            process_command = Popen([docker_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()
            if (stderr):
                print(stderr)
            else:
                print(stdout)
                list_containers.append(stdout)
            num_container+=1
        for container in list_containers:
            docker_wait= 'docker wait ' + container
            execute_wait= Popen([docker_wait], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = execute_wait.communicate()
            if (stderr):
                print(stderr)
            else:
                print(stdout)
        docker_log= 'docker logs cores_' + str(cores_per_container) + '_container_' + str(launch_containers-1)
        execute_log= Popen([docker_log], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = execute_log.communicate()
        if (stderr):
            print(stderr)
        else:
            f = open('times_contention.csv', 'a')
            writer = csv.writer(f)
            for row in stdout.split('\n'):
                if ': ' in row:
                    values = row.split(': ')
                    if(values[0] == 'ha tardado'):
                            # write row in csv format in file
                            time_exec= values[1].split('-')[0]
                            writer.writerow([str(cores_per_container), str(launch_containers), time_exec])
            f.close()
        docker_prune= "docker container prune -f"
        execute_prune= Popen([docker_prune], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = execute_prune.communicate()
print("Finish Oversubscription testing")

                       
