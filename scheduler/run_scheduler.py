# Runs all the complete policies for a given test specified in the json parameters file.
# In parameters file must specify the resource and the arrival time modes of the requests.
from email import policy
from statistics import stdev
import sys
from subprocess import Popen, PIPE, STDOUT
import json
import time
from unicodedata import name

def main():
    try:
        if len(sys.argv) != 4:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 3")
            raise NameError('Ingresar la cantidad de iteraciones')

        iterations= int(sys.argv[1])
        initial_containers=int(sys.argv[2])
        name_test= str(sys.argv[3])

        if(initial_containers == 8):
            folder_test=  "mkdir Data/log/" + name_test
            process_command = Popen([folder_test], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()
        
        for policy_type in ["fcfs" , "priority"]:
            
            if(initial_containers == 8):
                folder_policy_type= "mkdir Data/log/" + policy_type 
                process_command = Popen([folder_policy_type], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                stdout, stderr = process_command.communicate()

            for policy_assignment in ["strict", "always_attend", "max_prop"]:

                n_containers= initial_containers
                if(initial_containers == 8):
                    folder_policy=  "mkdir Data/log/" + policy_type + '/' + policy_assignment 
                    process_command = Popen([folder_policy], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                    stdout, stderr = process_command.communicate()

                for i in range(iterations):

                    for tf_version in ["maleable" , "original"]:
                    
                        with open('Scheduler-host/parameters.json', 'r+') as f:
                            variables = json.load(f)
                            variables["number_containers"] = n_containers
                            variables["policy"] = policy_type
                            variables["assignment_policy"] = policy_assignment
                            variables["tf_version"] = tf_version
                            variables["requests_file"] = "request_file_" + name_test + "_" + str(n_containers) + ".txt"
                            variables["get_requests"] = "file"
                            if(policy_assignment == "strict") and (tf_version == "maleable") and (policy_type == "fcfs"):
                                variables["get_requests"] = "create"
                                file_requests=  "nul > " + variables["requests_file"]
                                process_command = Popen([file_requests], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                                stdout, stderr = process_command.communicate()
                            f.seek(0) # <--- should reset file position to the beginning.
                            json.dump(variables, f) 
                            f.truncate()     # remove remaining part

                        print ("Execute scheduler...")
                        scheduler_command= 'python3 Scheduler-host/scheduler.py'
                        process_command = Popen([scheduler_command], stderr=PIPE, universal_newlines=True, shell=True)
                        stderr = process_command.communicate()

                        if(len(stderr)):
                            print(stderr)
                        else:
                            print("Execution correct")
                    
                        print("Move results...")
                        move_results= "cd Data/log/" +  policy_type + '/' + policy_assignment + " && mkdir " + str(n_containers) + "Contenedores_" + tf_version + " && find ../../ -maxdepth 1 -type f -exec mv {} " + str(n_containers) + "Contenedores_" + tf_version  + " \;"
                        process_command = Popen([move_results], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                        stdout, stderr = process_command.communicate()
                        if(len(stderr)):
                            print(stderr)
                        else:
                            print(stdout)

                        cp_outputs= "cd Data/log/" +   policy_type + '/' + policy_assignment +  "/" + str(n_containers) + "Contenedores_" + tf_version + " && mkdir Outputs && mv ../../../../../models/output_* Outputs"
                        process_command = Popen([cp_outputs], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                        stdout, stderr = process_command.communicate()
                        if(len(stderr)):
                            print(stderr)
                        else:
                            print(stdout)
                        
                        print("Wait 2 minutes...")
                        time.sleep(120)
                    n_containers*=2
        if(n_containers == 128):
            folder_test=  "mv Data/log/" + policy_type + " Data/log/" + name_test
            process_command = Popen([folder_test], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()
            move_requests_files= "mv request_file_* Data/log/" + name_test
            process_command = Popen([move_requests_files], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
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
   