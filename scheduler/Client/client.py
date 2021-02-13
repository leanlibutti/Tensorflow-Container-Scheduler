import os
import socket 
import sys
import threading
import logging
from subprocess import Popen, PIPE, STDOUT
import signal
from functools import partial
from trace import TraceLog
import time

mutex_eventlogs = threading.Lock()
event_logs= TraceLog(12)

filename_path= '/home/Data/log/log-'+str(threading.get_ident())

# Mutex para acceder con exclusión mutua a la información del sistema
mutex_finalize = threading.Lock()
finalize=False

logging.basicConfig(filename=filename_path,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

def receiveSignal(socket_scheduler, signalNumber, frame):
    
    try:
        print('Recieve signal finalize')

        mutex_eventlogs.acquire()
        event_logs.save_event(5, threading.current_thread().ident, 0)
        mutex_eventlogs.release()

        # Enviar finalización de TF al Scheduler
        socket_scheduler.send(bytes('finalize', 'utf-8'))

        mutex_finalize.acquire()
        finalize=True
        mutex_finalize.release()

        logging.info("Wait ACK from scheduler...")
        ack = socket_scheduler.recv(1).decode('utf-8')

        logging.info('Send finalize message')
    except:
        logging.info("Unexpected error in handle signal :(")

def attentionUpdate(socket_scheduler, pid_tf):

    print('Attention Update Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    execute_command=False

    try:
        mutex_finalize.acquire()    
        while not finalize:

            mutex_finalize.release()
            
            logging.info('Wait scheduler update message')
            signal = socket_scheduler.recv(2).decode('utf-8')
            paralellism = socket_scheduler.recv(2).decode('utf-8')

            logging.info("Recieve Change Parallelism: Signal="+ str(signal)+" Parallelism="+str(paralellism))

            mutex_eventlogs.acquire()
            event_logs.save_event(4, threading.current_thread().ident, int(signal))
            mutex_eventlogs.release()

            if signal == '10':
                # Cambiar el paralelismo inter
                os.environ["INTER_PARALELLISM"]  = paralellism 
                kill_command= "kill -10 " + str(pid_tf)
                logging.info('Change Inter Parallelism: ' + str(paralellism))
                execute_command=True

            else:
                if signal == '12':
                    # Cambiar el paralelismo intra
                    os.environ["INTRA_PARALELLISM"]  = paralellism 
                    kill_command= "kill -12 " + str(pid_tf)
                    logging.info('Change Intra Parallelism: ' + str(paralellism))
                    execute_command=True
            
            if execute_command:
                logging.info("Execute parallelism change...")
                process_command = Popen(kill_command, shell=True)
                execute_command=False

            mutex_finalize.acquire()
        mutex_finalize.release()
    
    except socket_scheduler.error as err:
        logging.info(err)
    except:
        logging.info("Unexpected error in update thread :(")

    logging.info("Finish update thread")

if __name__ == "__main__":

    try:
        logging.info("Client for Instance TF")

        if len(sys.argv) != 2:
            logging.info("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 1")
            raise NameError('Invalid amount of arguments')

        logging.info("Connecting Network...")
        
        # Obtener Ip de la red docker
        '''
        network_command= Popen(["docker network inspect docker0 --format {{.IPAM.Config}}"], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = network_command.communicate()

        if (len(stderr)):
            print(stderr)
        else:
            print("IP of network docker: ", stdout[2:12])
            network_ip= stdout[2:12]
            port=8080
        '''

        socket_scheduler= socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        socket_scheduler.connect(('172.17.0.1', 65000))

        # Recibir mensajes con el algoritmo TF a ejecutar y el paralelismo
        algorithm = sys.argv[1]
        logging.info('Algorithm recieved for parameter: '+ algorithm)

        event_logs.save_event(0, threading.current_thread().ident, 0)

        # Recibir el ID de cliente del planificador
        logging.info('Wait client ID...')
        client_id= socket_scheduler.recv(1).decode('utf-8')
        logging.info('Client ID recieved: '+ str(client_id))

        # Recibir paralelismo del planificador
        logging.info('Wait parallelism...')
        inter_parallelism= socket_scheduler.recv(1).decode('utf-8')
        logging.info('Inter parallelism recieved: ' + str(inter_parallelism))
        intra_parallelism= socket_scheduler.recv(1).decode('utf-8')
        logging.info('Intra parallelism recieved: ' + str(intra_parallelism))

        # Preparar comando de ejecución para TF
        tf_command = "cd /home/Data/models && " + 'python3 ' + algorithm + '.py ' + str(inter_parallelism) + ' ' + str(intra_parallelism) + ' ' + str(os.getpid())
        #command = "ls" 

        event_logs.save_event(1, threading.current_thread().ident, inter_parallelism+intra_parallelism)

        # Ejecutar comando TF
        logging.info('Execute TF algrithm in background...')
        tf_command_execute = Popen(tf_command, shell=True)

        # Esperar a que inicie correctamente el programa de TF
        time.sleep(2)

        event_logs.save_event(2, threading.current_thread().ident, 0)

        # Ejecutar comando para conocer el PID del proceso TF
        logging.info('Get TF PID...')
        ps_command= "ps -C python3 --no-headers -o pid"
        ps_command_execute = Popen(ps_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = ps_command_execute.communicate()

        if(stderr):
            logging.info('Error en popen: ' + stderr)
        else:
            logging.info('Salida de popen:' + stdout)

        # Obtener PID del proceso TF a partir del comando PS
        pid_tf= stdout.splitlines(0)[0][3:]
        logging.info('TF PID: ' + str(pid_tf))

        logging.info("Add signal handle...")
        signal.signal(signal.SIGUSR1, partial(receiveSignal, socket_scheduler))

        # Crear hilo para la atención de solicitudes
        logging.info("Creating update attention thread...")
        update_thread = threading.Thread(target=attentionUpdate, args=(socket_scheduler, pid_tf,))

        # Ejecutar hilo creado
        update_thread.start()

        # Hacer el join del hilo update
        update_thread.join()
        
        logging.info("Save log in CSV format...")
        event_logs.save_CSV('/home/Data/log')

        # Cerrar conexión del cliente con el scheduler
        logging.info("Close client socket")
        socket_scheduler.close()
        
        logging.info("Finish program :)")

    except (SyntaxError, IndentationError, NameError) as err:
        logging.info(err)
    except:
        logging.info("Unexpected error :(")

