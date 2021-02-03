import os
import socket 
import sys
import threading
import logging
from subprocess import Popen, PIPE, STDOUT
import signal
from functools import partial
from trace import TraceLog

mutex_eventlogs = threading.Lock()
event_logs= TraceLog(12)

filename_path= '/home/Data/log/log-'+str(threading.get_ident())

logging.basicConfig(filename=filename_path,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

def receiveSignal(socket_scheduler, signalNumber, frame):
    
    print('Recieve signal finalize')

    mutex_eventlogs.acquire()
    event_logs.save_event(5, threading.current_thread().ident, 0)
    mutex_eventlogs.release()

    # Enviar finalización de TF al Scheduler
    socket_scheduler.send(bytes('finalize', 'utf-8'))

    logging.info('Send finalize message')

def attentionUpdate(socket_scheduler, pid_tf):

    print('Attention Update Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    while True:

        logging.info('Wait scheduler update message')
        signal = socket_scheduler.recv(1024).decode('utf-8')
        paralellism = socket_scheduler.recv(1024).decode('utf-8')

        mutex_eventlogs.acquire()
        event_logs.save_event(4, threading.current_thread().ident, int(signal))
        mutex_eventlogs.release()

        if signal == '10':

            # Cambiar el paralelismo inter
            os.environ["INTER_PARALELLISM"]  = paralellism 
            kill_command= "kill -10 " + str(pid_tf)
            logging.info('Change Inter Parallelism')

        else:
            
            # Cambiar el paralelismo intra
            os.environ["INTRA_PARALELLISM"]  = paralellism 
            kill_command= "kill -12 " + str(pid_tf)
            logging.info('Change Intra Parallelism')

        process_command = Popen([kill_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()

if __name__ == "__main__":

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
    logging.info('Algorithm Recieved: '+ algorithm)

    event_logs.save_event(0, threading.current_thread().ident, 0)

    # Recibir el ID de cliente del planificador
    client_id= socket_scheduler.recv(1024).decode('utf-8')

    # Recibir paralelismo del planificador
    inter_parallelism= socket_scheduler.recv(1024).decode('utf-8')
    intra_parallelism= socket_scheduler.recv(1024).decode('utf-8')
    logging.info('Inter and Intra Parallelism Recieved: ' + str(inter_parallelism), ' - ', str(intra_parallelism))

    # Preparar comando de ejecución para TF
    command = "cd /home/Data/models && " + 'python3 ' + algorithm + '.py ' + str(inter_parallelism) + ' ' + str(intra_parallelism) + ' ' + str(os.getpid())

    event_logs.save_event(1, threading.current_thread().ident, inter_parallelism+intra_parallelism)

    # Ejecutar comando TF
    process_command = Popen([command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    stdout, stderr = process_command.communicate()

    if (len(stderr)):
        logging.info(stderr)
        event_logs.save_event(2, threading.current_thread().ident, 0)
    else:

        event_logs.save_event(3, threading.current_thread().ident, 0)

        # Ejecutar comando para conocer el PID del proceso TF
        ps_command= "ps -C bash --no-headers -o pid"
        process_command = Popen([ps_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()

        # Obtener PID del proceso TF a partir del comando PS
        pid_tf= stdout.splitlines(0)[0][3:]

        logging.info("Add Signal Handle...")
        signal.signal(signal.SIGUSR1, partial(receiveSignal, socket_scheduler))

        logging.info("Creating update attention thread...")

        # Crear hilo para la atención de solicitudes
        update_thread = threading.Thread(target=attentionUpdate, args=(socket_scheduler, pid_tf,))

        # Ejecutar hilo creado
        update_thread.start()

        # Hacer el join del hilo creado
        update_thread.join()

        event_logs.save_CSV('/home/Data/log')

    # Cerrar conexión del cliente con el scheduler
    socket_scheduler.close()
    logging.info("Close client socket")
    logging.info("Finish program :)")

