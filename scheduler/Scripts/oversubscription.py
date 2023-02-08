from subprocess import Popen, PIPE, STDOUT
import time
import csv
model_name= 'keras_example_resnet.py'
interparalelismo=1
f = open('times_oversubscription.csv', 'w')
writer = csv.writer(f)
header = ['Cores', 'Intra', 'Time']
# write the header
writer.writerow(header)
# for cores in [1,2,4,8,16,24,32,48,64]:
for cores in [1]:
    # for intraparalelismo in [1,2,4,8,16,24,32,48,64]:
    for intraparalelismo in [16]:
        docker_command= 'docker run -dit --cpus=' + str(cores) + ' --name cores_'+  str(cores) + '_intra_' +  str(intraparalelismo) + ' --volume=$HOME/scheduler:/home/scheduler tf_oversubscription ' + str(interparalelismo) + ' ' + str(intraparalelismo) + ' /home/scheduler/models/' + model_name + ' /home/scheduler/logs_oversubscription/execution_' + str(cores) + '_' + str(intraparalelismo) + '.txt'
        print(docker_command)
        # Ejecutar comando (con os.p)
        # Los primeros 12 caracteres de stdout son el Execution container request:container ID
        process_command = Popen([docker_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()
        if (stderr):
            print(stderr)
        else:
            print(stdout)
            docker_wait= 'docker wait ' + stdout
            execute_wait= Popen([docker_wait], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = execute_wait.communicate()
            if (stderr):
                print(stderr)
            else:
                print(stdout)
            docker_log= 'docker logs cores_' + str(cores) + '_intra_' + str(intraparalelismo)
            execute_log= Popen([docker_log], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = execute_log.communicate()
            if (stderr):
                print(stderr)
            else:
                for row in stdout.split('\n'):
                    if ': ' in row:
                        values = row.split(': ')
                        if(values[0] == 'ha tardado'):
                                # write row in csv format in file
                                time_exec= values[1].split('-')[0]
                                writer.writerow([str(cores), str(intraparalelismo), time_exec])
            docker_prune= "docker container prune -f"
            execute_prune= Popen([docker_prune], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = execute_prune.communicate()
f.close()
print("Finish Oversubscription testing")

                       
