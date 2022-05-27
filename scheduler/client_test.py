import os
import socket 
import sys
import threading
import logging
import multiprocessing
from subprocess import Popen, PIPE, STDOUT
import time
import traceback
import signal
from functools import partial

finalize= False

filename_path= '/home/Scheduler/Data/log/log-'+str(threading.current_thread().ident)

logging.basicConfig(filename=filename_path,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

def receiveSignal(signalNumber, frame):

    global finalize
    
    try:
        logging.info('Recieve signal finalize')

        finalize=True

        # Enviar finalización de TF al Scheduler
        logging.info('Send finalize message')
    except:
        logging.info("Unexpected error in handle signal :(")

if __name__ == "__main__":
    try:
        
        number_thread=1

        logging.info("Client for Instance TF")

        if len(sys.argv) != 2:
            #logging.info("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 1")
            raise NameError('Invalid amount of arguments')

        logging.info("Connecting Network...")

        # socket_scheduler= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # socket_scheduler.connect(('172.17.0.1', 65000))

        # Recibir mensajes con el algoritmo TF a ejecutar y el paralelismo
        algorithm = sys.argv[1]
        logging.info('Algorithm recieved for parameter: '+ algorithm)

        # Get cpu cores
        cores_cpu= multiprocessing.cpu_count()-1
        #logging.info('Cores CPU: ' + str(cores_cpu))
        
        # Write parallelism in file so that Tensorflow can read it
        #f= open("/home/leandro/tf_parallelism.txt","w+") # Usado en Maquina local
        f= open("/root/tf_parallelism.txt","w+") # Usado en esfinge
        f.write(str(1) + " " + str(cores_cpu))
        f.close()
        
        # Set tf version
        tf_use= 'original'

        if tf_use == 'original':
            file_log_tf= 'output_' + str(threading.current_thread().ident)  + '.txt'
        
        # Prepare TF command (with max cpu cores in inter and intra parallelism)
        if tf_use == 'original':
            tf_command = "cd /home/Scheduler/models/ && logsave -a " + file_log_tf + " python3 "  +  algorithm + '.py ' + str(1) + ' ' +str(8) + ' ' + str(os.getpid())
        else:
            #tf_command = "cd /home/Scheduler/models/ && " + 'python3 ' + algorithm + '.py ' + str(2) + ' ' + str(cores_cpu)  + ' ' +  str(os.getpid()) + ' > /home/Scheduler/models/output_' + str(threading.current_thread().ident) + '.txt'
            tf_command = "cd /home/Scheduler/models/ &&  logsave -a " + file_log_tf + ' python3 ' + algorithm + '.py ' + str(1) + ' ' + str(cores_cpu)  + ' ' +  str(os.getpid())

        # Ejecutar comando TF
        logging.info('Execute TF algrithm in background...')
        tf_command_execute = Popen(tf_command, shell=True)
            
        # Esperar a que inicie correctamente el programa de TF
        time.sleep(2)

        # Ejecutar comando para conocer el PID del proceso TF
        #logging.info('Get TF PID...')
        ps_command= "ps -C python3 --no-headers -o pid"
        ps_command_execute = Popen(ps_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = ps_command_execute.communicate()

        if(stderr):
            logging.info('Error en popen: ' + stderr)
        else:
            logging.info('Salida de popen:' + stdout)

        # Obtener PID del proceso TF a partir del comando PS
        #pid_tf= stdout.splitlines(0)[1][3:]
        pids_tf= stdout.splitlines(0)
        if len(pids_tf) > 1:
            pid_tf= int(pids_tf[1])
        else:
            pid_tf= int(pids_tf[0])
        logging.info('TF PID: ' + str(pid_tf))

        logging.info("Add signal handle...")
        signal.signal(signal.SIGUSR1, partial(receiveSignal))

        while (not finalize):
            time.sleep(10)

        logging.info("Save log in CSV format...")

        log_name= 'client_events_' + str(threading.current_thread().ident) + '.txt'

        logging.info("Finish program :)")

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt")
    except BaseException as e:
        logging.info(repr(e))
        logging.info(traceback.format_exc())
        logging.info("Base error")
    except (SyntaxError, IndentationError, NameError) as err:
        logging.info(err)
    except:
        logging.info("Unexpected error :(")