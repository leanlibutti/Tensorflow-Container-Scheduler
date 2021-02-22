import os
import socket 
import sys
import threading
import logging
from subprocess import Popen, PIPE, STDOUT
import signal
from functools import partial
import time
from Commons.trace import TraceLog

mutex_eventlogs = threading.Lock()
event_logs= TraceLog(1)

filename_path= '/home/Scheduler/Data/log/log-'+str(threading.current_thread().ident)

# Mutex para acceder con exclusión mutua a la información del sistema
mutex_finalize = threading.Lock()
finalize=False

# Variable condición utilizada para avisar al hilo Atencion de que hay pedidos pendientes en alguna cola.
cv_update = threading.Condition()
signal=''
parallelism=''

logging.basicConfig(filename=filename_path,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

def receiveSignal(socket_scheduler, number_thread, signalNumber, frame):

    global finalize
    
    try:
        logging.info('Recieve signal finalize')

        mutex_eventlogs.acquire()
        event_logs.save_event(5, number_thread, 0)
        mutex_eventlogs.release()

        # Enviar finalización de TF al Scheduler
        logging.info('Send finalize message')
        socket_scheduler.send(bytes('finalize', 'utf-8'))

        mutex_finalize.acquire()
        finalize=True
        mutex_finalize.release()
    except:
        logging.info("Unexpected error in handle signal :(")

def attention_socket(socket_scheduler, number_thread):
    global parallelism
    global signal
    continue_exec=True
    while continue_exec:
        try:
            logging.info('Wait message from scheduler...')
            data = socket_scheduler.recv(2).decode('utf-8')

            if data=='10' or data=='12':   
                logging.info("Recieve signal: " + str(data)) 
                signal= data  
                paralellism = socket_scheduler.recv(2).decode('utf-8')
                logging.info("Parallelism revieved: " + str(paralellism))
                with cv_update:
                    cv_update.notify()
            else:
                logging.info("ACK from scheduler: " + str(data))
                continue_exec=False
        except socket_scheduler.timeout:
            logging.info("Socket timeout")
    with cv_update:
        cv_update.notify()
    logging.info("Finish attention socket thread")

def attentionUpdate(pid_tf, number_thread):

    print('Attention Update Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    global parallelism
    global signal
    global finalize

    try:
        mutex_finalize.acquire()    
        while not finalize:

            mutex_finalize.release()

            logging.info('Wait scheduler update message... - Finalize= ' + str(finalize))
            with cv_update:
                cv_update.wait()

            if signal=='10' or signal=='12':
                logging.info("Recieve Change Parallelism: Signal="+ str(signal)+" Parallelism="+str(parallelism))
                mutex_eventlogs.acquire()
                event_logs.save_event(4, number_thread, int(signal))
                mutex_eventlogs.release()

                if signal == '10':
                    # Cambiar el paralelismo inter
                    os.environ["INTER_PARALELLISM"]  = parallelism
                    kill_command= "kill -10 " + str(pid_tf)
                    logging.info('Change Inter Parallelism: ' + str(parallelism))
                else:
                    if signal == '12':
                        # Cambiar el paralelismo intra
                        os.environ["INTRA_PARALELLISM"]  = parallelism
                        kill_command= "kill -12 " + str(pid_tf)
                        logging.info('Change Intra Parallelism: ' + str(parallelism))
                
                logging.info("Execute parallelism change...")
                process_command = Popen(kill_command, shell=True)

            mutex_finalize.acquire()
        mutex_finalize.release()
    
    except socket_scheduler.error as err:
        logging.info(err)
    except:
        logging.info("Unexpected error in update thread :(")

    logging.info("Finish update thread")

if __name__ == "__main__":

    try:
        number_thread=1

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

        event_logs.save_event(0, 0)

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
        tf_command = "cd /home/Scheduler/models && " + 'python3 ' + algorithm + '.py ' + str(inter_parallelism) + ' ' + str(intra_parallelism) + ' ' + str(os.getpid())
        #command = "ls" 

        event_logs.save_event(1, 0, inter_parallelism, intra_parallelism)

        # Ejecutar comando TF
        logging.info('Execute TF algrithm in background...')
        tf_command_execute = Popen(tf_command, shell=True)

        # Esperar a que inicie correctamente el programa de TF
        time.sleep(2)

        event_logs.save_event(2, 0, 0)

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
        signal.signal(signal.SIGUSR1, partial(receiveSignal, socket_scheduler, 0))

        # Crear hilo para la atención de solicitudes
        logging.info("Creating update attention thread...")
        update_thread = threading.Thread(target=attentionUpdate, args=(pid_tf,number_thread,))
        number_thread= number_thread+1

        # Crear hilo para la atención de solicitudes
        logging.info("Creating socket attention thread...")
        socket_thread = threading.Thread(target=attention_socket, args=(socket_scheduler,number_thread,))
        number_thread=number_thread+1

        # Ejecutar hilos
        update_thread.start()
        event_logs.add_thread()
        socket_thread.start()
        event_logs.add_thread()

        # Hacer el join de los hilos
        update_thread.join()
        socket_thread.join()
        
        logging.info("Save log in CSV format...")

        log_name= 'client_events_' + str(client_id) + '.txt'

        event_logs.save_CSV('/home/Scheduler/Data/log/',log_name)
        # Cerrar conexión del cliente con el scheduler
        logging.info("Close client socket")
        socket_scheduler.close()

        logging.info("Finish program :)")

    except (SyntaxError, IndentationError, NameError) as err:
        logging.info(err)
    except socket_scheduler.error as err:
        logging.info(err)
        logging.info("Error in socket")
    except:
        logging.info("Unexpected error :(")

