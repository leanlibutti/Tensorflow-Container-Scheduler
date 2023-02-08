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
    parser.add_argument('-cp', '--cant_priorities', type=int, default=1, help= 'number of priorities used (default 1)')
    args = parser.parse_args()
    name_test= args.name_test
    policies= args.policies.split(' ')
    assigment_policies= args.assigment_policies.split(' ')
    tf_versions= args.tf_version.split(' ')
    cant_priorities= args.cant_priorities
    f = open(name_test+'.csv', "w")
    f.write('Containers, Policy, Asignment Policy, Tf Version, Priority, TME, TMR, TMER, Recursos, Productividad, TT \n')
    for policy in policies:
        n_containers=8
        for i in range(5):
            for assigment_policy in assigment_policies:
                for tf_version in tf_versions:
                    run_trace=  "python3 Scheduler-host/Commons/trace.py -d Data/log/" + name_test + "/" + policy + "/" + assigment_policy + "/" +  str(n_containers) + "Contenedores_" + tf_version + "/" + " -f gantt_events.txt -c " + str(n_containers) + " -n " + name_test + " -p " + policy + ' -cp ' + str(cant_priorities)
                    print(run_trace)
                    process_command = Popen([run_trace], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                    stdout, stderr = process_command.communicate()
                    # print(stdout)
                    lines = stdout.split('\n')
                    if(stdout):
                        if policy == 'priority':
                            for j in range(cant_priorities):
                                line_file= str(n_containers) + ',' + policy + ',' +  assigment_policy + ',' + tf_version + ',' + str(j) + ',' +lines[j] + '\n'
                                f.write(line_file) 
                                print(line_file)
                        else:
                            line_file= str(n_containers) + ',' + policy + ',' + assigment_policy + ',' + tf_version + ',1,' + lines[0] + '\n'
                            f.write(line_file) 
                            print(line_file)
                    else:
                        print(stderr)
                        raise Exception('Error in run trace.py')
            n_containers*=2
    f.close()
        
if __name__ == "__main__":
    main()