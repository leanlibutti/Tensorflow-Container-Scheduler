from statistics import stdev
import sys
from subprocess import Popen, PIPE, STDOUT
import json
import time
from unicodedata import name

def main():
    if len(sys.argv) != 2:
        print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 1")
        raise NameError('Ingresar la cantidad de iteraciones')
    name_test= str(sys.argv[1])
    f = open(name_test+'.csv', "w")
    n_containers=8
    for i in range(5):
        for policy in ["strict", "always_attend", "max_prop"]:
            for tf_version in ["maleable" , "original"]:
                run_trace=  "python3 Scheduler-host/Commons/trace.py Data/log/" + name_test + "/" + policy + "/" + str(n_containers) + "Contenedores_" + tf_version + "/" + " gantt_events.txt " + str(n_containers)
                print(run_trace)
                process_command = Popen([run_trace], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                stdout, stderr = process_command.communicate()
                if(stdout):
                    f.write(str(n_containers) + ',' + policy + ',' + tf_version + ',' + stdout) 
                else:
                    print(stderr)
                    raise Exception('Error in run trace.py')
        n_containers*=2
    f.close()
        
if __name__ == "__main__":
    main()