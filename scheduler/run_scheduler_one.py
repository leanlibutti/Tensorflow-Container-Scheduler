# run the scheduler once, indicating the test name, policy type, assigment_policy, number of containers and tf version.
# The test is saved in Data/log/Pruebas_espana
from statistics import stdev
import sys
from subprocess import Popen, PIPE, STDOUT
import json
import time
from unicodedata import name
import argparse

def main():
    try:
        if len(sys.argv) != 6:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 5 (name test, policy, assigment_policy, containers and tf version")
            raise NameError('Parameters count is wrong')
        parser = argparse.ArgumentParser()
        parser.add_argument('--name_test', type=str, required=True, help='name of test (required)')
        parser.add_argument('--policy', type=str, required=True, help='policy to be executed (fcfs or priority) (required)')
        parser.add_argument('--assigment_policy', type=str, required=True, help= 'resource allocation strategies that were used (strict or always_attend or max_prop) (required)')
        parser.add_argument('--containers', type=int, required=True, help='number of container to be executed (required)) (required)')
        parser.add_argument('--tf_version', type=str, required=True, help= 'tensorflow versions used (malleable or original) (required)')
        args = parser.parse_args()
        name_test= args.name_test
        policy= args.policy
        policy_assignment= args.assigment_policy
        n_containers= args.containers
        tf_version= args.tf_version  
        move_request= "mv Data/log/" + name_test + "/request_file_" + name_test + "_" + str(n_containers) + ".txt ." 
        process_command = Popen([move_request], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()
        with open('Scheduler-host/parameters.json', 'r+') as f:
            variables = json.load(f)
            variables["number_containers"] = n_containers
            variables["policy"] = policy
            variables["assignment_policy"] = policy_assignment
            variables["tf_version"] = tf_version
            variables["requests_file"] = "request_file_" + name_test + "_" + str(n_containers) + ".txt"
            variables["get_requests"] = "file"
            f.seek(0) # <--- should reset file position to the beginning.
            json.dump(variables, f) 
            f.truncate()     # remove remaining part

        print ("Execute scheduler...")
        scheduler_command= 'python3 Scheduler-host/scheduler.py > execution_scheduler.txt'
        process_command = Popen([scheduler_command], stderr=PIPE, universal_newlines=True, shell=True)
        stderr = process_command.communicate()

        if(len(stderr)):
            print(stderr)
        else:
            print("Execution correct")
    
        print("Move results...")
        move_results= "cd Data/log/" + name_test + '/' + policy  + " && mkdir " + str(n_containers) + "Contenedores_" + tf_version + " && find ../../ -maxdepth 1 -type f -exec mv {} " + str(n_containers) + "Contenedores_" + tf_version  + " \;"
        process_command = Popen([move_results], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()
        if(len(stderr)):
            print(stderr)
        else:
            print(stdout)

        cp_outputs= "cd Data/log/" + name_test + '/' + policy  +  "/" + str(n_containers) + "Contenedores_" + tf_version + " && mkdir Outputs && mv ../../../../../models/output_* Outputs"
        process_command = Popen([cp_outputs], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()
        if(len(stderr)):
            print(stderr)
        else:
            print(stdout)

        move_request=  "mv request_file_" + name_test + "_" + str(n_containers) + ".txt " + "Data/log/" + name_test
        process_command = Popen([move_request], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()
    except BaseException as e:
        print(repr(e))
        print("Base error")
    except (SyntaxError, IndentationError, NameError) as err:
        print(err)
    except:
        print("Unexpected error :(")

if __name__ == "__main__":
    main()
   