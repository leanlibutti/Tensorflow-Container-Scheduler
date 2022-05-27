import sys
from subprocess import Popen, PIPE, STDOUT
import json
import time


def main():
    try:
        if len(sys.argv) != 3:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 2")
            raise NameError('Ingresar la cantidad de iteraciones')

        iterations= int(sys.argv[1])
        n_containers=int(sys.argv[2])

        for i in range(iterations):
            
            with open('Scheduler-host/parameters.json', 'r+') as f:
                variables = json.load(f)
                variables["number_containers"] = n_containers
                f.seek(0) # <--- should reset file position to the beginning.
                json.dump(variables, f) 
                f.truncate()     # remove remaining part

            print ("Execute scheduler...")
            scheduler_command= 'python3.8 Scheduler-host/scheduler.py'
            process_command = Popen([scheduler_command], stderr=PIPE, universal_newlines=True, shell=True)
            stderr = process_command.communicate()

            if(len(stderr)):
                print(stderr)
            else:
                print("Execution correct")
        
            print("Move results...")
            move_results= "cd Data/log && mkdir " + str(n_containers) + "Contenedores && find . -maxdepth 1 -type f -exec mv {} " + str(n_containers) + "Contenedores \;"
            process_command = Popen([move_results], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()
            if(len(stderr)):
                print(stderr)
            else:
                print(stdout)

            cp_outputs= "cd Data/log/" +  str(n_containers) + "Contenedores && mkdir Outputs && mv ../../../models/output_* Outputs"
            process_command = Popen([cp_outputs], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()
            if(len(stderr)):
                print(stderr)
            else:
                print(stdout)
            n_containers*=2

            print("Wait 2 minutes...")
            time.sleep(120)
    except BaseException as e:
        print(repr(e))
        print("Base error")
    except (SyntaxError, IndentationError, NameError) as err:
        print(err)
    except socket_schedule.error as err:
        print(err)
        print("Error in socket")
    except:
        print("Unexpected error :(")

if __name__ == "__main__":
    main()
   