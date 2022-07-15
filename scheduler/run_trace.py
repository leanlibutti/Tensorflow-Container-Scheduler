from statistics import stdev
import sys
from subprocess import Popen, PIPE, STDOUT
import json
import time
from unicodedata import name
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name_test', type=str, required=True, help='name of test (required)')
    parser.add_argument('--policies', type=list, default=["fcfs", "priority"], help='policies executed (fcfs and/or priority)')
    parser.add_argument('--assigment_policies', type=list, default=["strict", "always_attend", "max_prop"], help= 'resource allocation strategies that were used (strict and/or always_attend and/or max_prop')
    parser.add_argument('--tf_version', type=list, default=["maleable" , "original"], help= 'tensorflow versions used (malleable and/or original)')
    args = parser.parse_args()
    name_test= args.name_test
    f = open(name_test+'.csv', "w")
    for policy in args.policies:
        n_containers=8
        for i in range(5):
            for assigment_policy in args.assigment_policies:
                for tf_version in args.tf_version:
                    run_trace=  "python3 Scheduler-host/Commons/trace.py Data/log/" + name_test + "/" + policy + "/" + assigment_policy + "/" +  str(n_containers) + "Contenedores_" + tf_version + "/" + " gantt_events.txt " + str(n_containers)
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