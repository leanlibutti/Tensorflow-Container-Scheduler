from statistics import stdev
import sys
from subprocess import Popen, PIPE, STDOUT
import json
import time
from unicodedata import name
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name_test', type=str, required=True, help='name of test (required)')
    parser.add_argument('-p', '--policies', type=str, default="fcfs priority", help='policies executed (fcfs and/or priority)')
    parser.add_argument('-a', '--assigment_policies', type=str, default="strict always_attend max_prop", help= 'resource allocation strategies that were used (strict and/or always_attend and/or max_prop')
    parser.add_argument('-t', '--tf_version', type=str, default="maleable original", help= 'tensorflow versions used (malleable and/or original)')
    args = parser.parse_args()
    name_test= args.name_test
    policies= args.policies.split(' ')
    assigment_policies= args.assigment_policies.split(' ')
    tf_versions= args.tf_version.split(' ')
    f = open(name_test+'.csv', "w")
    for policy in policies:
        n_containers=8
        for i in range(5):
            for assigment_policy in assigment_policies:
                for tf_version in tf_versions:
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