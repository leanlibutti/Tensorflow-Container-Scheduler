import os
import socket 
import sys
import threading
import logging
from subprocess import Popen, PIPE, STDOUT
import signal
from functools import partial
import time
import datetime
from Commons.trace import TraceLog
from Commons import json_data_socket
import multiprocessing
import traceback

mutex_eventlogs = threading.Lock()
event_logs= TraceLog(1)

filename_path= '/home/Scheduler/Data/log/log-'+str(threading.current_thread().ident)

# Mutex para acceder con exclusión mutua a la información del sistema
mutex_finalize = threading.Lock()
finalize=False

# Variable condición utilizada para avisar al hilo Atencion de que hay pedidos pendientes en alguna cola.
cv_update = threading.Semaphore(0)
cv_live_control= threading.Condition()
mutex_inter_up= threading.Lock()
inter_parallelism_up=0
mutex_intra_up= threading.Lock()
intra_parallelism_up=0

tf_use=""

logging.basicConfig(filename=filename_path,
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

def receiveSignal(socket_scheduler, signalNumber, frame):

    global finalize
    
    try:
        logging.info('Recieve signal finalize')

        mutex_eventlogs.acquire()
        event_logs.save_event(5, 0, 0)
        mutex_eventlogs.release()

        # Enviar finalización de TF al Scheduler
        logging.info('Send finalize message')
        data= {
            "status": 'exit'
        }
        json_data_socket._send(socket_scheduler, data)

        mutex_finalize.acquire()
        finalize=True
        mutex_finalize.release()
    except:
        logging.info("Unexpected error in handle signal :(")
 
# Reemplaza linea de texto en un archivo       
def replace_line(file_name, line_num, text):
    f= open(file_name,"r")
    lines = f.readlines()
    #logging.info("Print before line: " + lines[line_num])
    lines[line_num] = text
    f.close()
    out = open(file_name, 'w')
    out.writelines(lines)
    #logging.info("Print after line: " + lines[line_num])
    out.close()
        
# Cambiar de forma progresiva el paralelismo inter o intra. Si es la primera peticion del contenedor
# el parámetro "parallelism" indica el paralelismo viejo. Caso contrario, indica el paralelismo nuevo.
def progressive_update_threads(inter_or_intra, parallelism, pid_tf):
    try: 
        filename= "/root/tf_parallelism.txt" # en esfinge
        #filename= "/home/leandro/tf_parallelism.txt" # en máquina local
        # Cambiar el paralelismo intra
        f= open(filename,"r")
        lines= f.readlines()
        f.close()
        parallelism_new = int(parallelism)
        if inter_or_intra==0:
            intra_parallelism= lines[0].split(' ')[1]
            parallelism_old = int(lines[0].split(' ')[0])
        else:
            inter_parallelism= lines[0].split(' ')[0]
            parallelism_old = int(lines[0].split(' ')[1])

        # Enviar unica señal de disminucion/aumento de paralelismo    
        # if inter_or_intra==0:
        #     replace_line(filename, 0, str(parallelism_new) + " " + str(intra_parallelism) + "\n")
        #     kill_command= "kill -10 " + str(pid_tf)
        #     logging.info('Change Inter Parallelism: ' + str(parallelism_new))
        # else:
        #     replace_line(filename, 0, str(inter_parallelism) + " " + str(parallelism_new)+ "\n")
        #     kill_command= "kill -12 " + str(pid_tf)
        #     logging.info('Change Intra Parallelism: ' + str(parallelism_new))
        # process_command = Popen(kill_command, shell=True)
        
        # En caso de que debe decrementarse el paralelismo, lo haremos progresivamente disminuyendo en la mitad en cada señal enviada a Tensorflow
        while (parallelism_old != parallelism_new):
            #logging.info("Vuelta del while")
            if (parallelism_old < parallelism_new) or ((parallelism_old-1) < parallelism_new):
                parallelism_old= parallelism_new
            else:
                parallelism_old= int(parallelism_old/2)
                # parallelism_old= int(parallelism_old-1)
            if inter_or_intra==0:
                replace_line(filename, 0, str(parallelism_old) + " " + str(intra_parallelism) + "\n")
                kill_command= "kill -10 " + str(pid_tf)
                logging.info('Change Inter Parallelism: ' + str(parallelism_old))
            else:
                replace_line(filename, 0, str(inter_parallelism) + " " + str(parallelism_old)+ "\n")
                kill_command= "kill -12 " + str(pid_tf)
                logging.info('Change Intra Parallelism: ' + str(parallelism_old))
            process_command = Popen(kill_command, shell=True)
            time.sleep(1)
    except: 
        logging.info("Error in Progressive Thread : maybe filename")
    logging.info("Finish Progressive Update Thread")

def live_control(socket_scheduler, number_thread, path_file):
    global finalize
    
    root_file= "/home/Scheduler/models/"

    try: 
        mutex_finalize.acquire()     
        while not finalize:
            mutex_finalize.release()
            with cv_live_control:
                cv_live_control.wait()
            logging.info("Live control wake up:" + str(finalize))
            mutex_finalize.acquire()     
            if not finalize:
                mutex_finalize.release()   
                logging.info("Path file TF: " + str(root_file+path_file))

                ti_file= os.path.getmtime(root_file+path_file)
                ti_now= datetime.datetime.now().timestamp()
                diff_time= ti_now - ti_file

                logging.info("Diff time: " + str(diff_time))

                if int(diff_time) < 20:
                    logging.info("Container is live!")
                    data= {
                        "status": 'live'
                    }
                else:
                    logging.info("Container is dead!")
                    data= {
                        "status": 'error'
                    }
                json_data_socket._send(socket_scheduler, data)
                mutex_finalize.acquire()
        mutex_finalize.release()
         
    except (SyntaxError, IndentationError, NameError) as err:
        logging.info(err)
    except socket_scheduler.error as err:
        logging.info(err)
        logging.info("Error in socket")
    except:
        logging.info("Unexpected error :(")
    logging.info("Finish live control thread")
    


def attention_socket(socket_scheduler, number_thread):
    continue_exec=True
    global inter_parallelism_up
    global intra_parallelism_up
    while continue_exec:
        try:
            logging.info('Wait message from scheduler...')
            data = json_data_socket._recv(socket_scheduler)
            logging.info('Intra and inter recieved:' + str(data["intra_parallelism"]) + ' - ' + str(data["inter_parallelism"]))
            if data["inter_parallelism"] > 0:  
                mutex_inter_up.acquire()
                inter_parallelism_up= data["inter_parallelism"]
                mutex_inter_up.release()
                logging.info(" Inter Parallelism revieved: " + str(data["inter_parallelism"]))
            if data["intra_parallelism"] > 0:
                mutex_intra_up.acquire()
                intra_parallelism_up= data["intra_parallelism"]
                mutex_intra_up.release()
                logging.info(" Intra Parallelism revieved: " + str(data["intra_parallelism"]))
            if ((data["inter_parallelism"] > 0) or (data["intra_parallelism"] >0)):
                cv_update.release()
            if data["inter_parallelism"] == -1:
                logging.info("ACK from scheduler")
                continue_exec=False
            if data["inter_parallelism"] == -2:
                logging.info("Wake up live control...")
                with cv_live_control:
                    cv_live_control.notify()    
        except socket_scheduler.timeout:
            logging.info("Socket timeout")
        except (SyntaxError, IndentationError, NameError) as err:
            logging.info(err)
        except:
            logging.info("Unexpected error :(")

    cv_update.release()
    logging.info("Finish attention socket thread")

def attentionUpdate(pid_tf, number_thread, inter_parallelism, intra_parallelism):

    #print('Attention Update Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    global inter_parallelism_up
    global intra_parallelism_up
    global finalize
    global tf_use
        
    try:
        #Enviar Señal de Actualizacion de hilos intra si es la version maleable
        if (tf_use=='maleable'):
            time.sleep(20)
            logging.info("Entry Progressive Update Thread")
            progressive_update_threads(1, intra_parallelism, pid_tf)

        mutex_finalize.acquire()        
        while not finalize:

            mutex_finalize.release()

            #logging.info('Wait scheduler update message... - Finalize= ' + str(finalize))
            cv_update.acquire()
                
            if (tf_use == 'maleable'):
                mutex_inter_up.acquire()
                logging.info('Intra parallelism before progressive update:' + str(intra_parallelism_up))
                if inter_parallelism_up>0:
                    # Cambiar el paralelismo inter
                    progressive_update_threads(0, inter_parallelism_up, pid_tf)
                    mutex_eventlogs.acquire()
                    event_logs.save_event(4, number_thread, 10)
                    mutex_eventlogs.release()
                    inter_parallelism_up=0
                mutex_inter_up.release()
                mutex_intra_up.acquire()
                if intra_parallelism_up>0:
                    progressive_update_threads(1, intra_parallelism_up, pid_tf)
                    mutex_eventlogs.acquire()
                    event_logs.save_event(4, number_thread, 12)
                    mutex_eventlogs.release()
                    intra_parallelism_up=0
                mutex_intra_up.release()
            else:
                logging.info('Not update because is original version of Tensorflow')
            mutex_finalize.acquire()
        # Despertar al hilo controlador de estado
        with cv_live_control:
            cv_live_control.notify()
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
            #logging.info("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 1")
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

        # Recibir informacion del planificador
        logging.info('Wait data...')
        #data= json_data_socket._recv(socket_scheduler)
            # read the length of the data
        length_str = ''
        data = json_data_socket._recv(socket_scheduler)
        logging.info('Client ID recieved: '+ str(data["container"]))
        logging.info('TF Use: '+ str(data["tf_use"]))
        logging.info('Inter parallelism recieved: ' + str(data["inter_parallelism"]))
        logging.info('Intra parallelism recieved: ' + str(data["intra_parallelism"]))

        # Get cpu cores
        # cores_cpu= multiprocessing.cpu_count()
        cores_cpu=16
        logging.info('Cores CPU: ' + str(cores_cpu))
        
        # Write parallelism in file so that Tensorflow can read it
        #f= open("/home/leandro/tf_parallelism.txt","w+") # Usado en Maquina local
        f= open("/root/tf_parallelism.txt","w+") # Usado en esfinge
        f.write(str(data["inter_parallelism"]) + " " + str(cores_cpu))
        # f.write(str(data["inter_parallelism"]) + " 12")
        f.close()
        
        # Set tf version
        tf_use= data["tf_use"]
        
        # Verify file
        '''
        f= open("/home/tf_parallelism.txt","r")
        #logging.info("Line in file: " + f.readlines()[0])
        f.close()
        

        logging.info('Execute TF warmup...')
        tf_command_warmup = "cd /home/Scheduler/models/ && logsave -a output_warmup_" + str(data["container"]) + ".txt python3 keras_example_resnet_warmup.py 1 1 1"
        tf_command_run = Popen(tf_command_warmup, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr =  tf_command_run.communicate()
        logging.info('Finish TF warmup!')
        '''

        if tf_use == 'original':
            file_log_tf= 'output_' + str(data["container"]) + '_original.txt'
        else:
            file_log_tf= 'output_' + str(data["container"]) + '_maleable.txt'
        
        # Prepare TF command (with max cpu cores in inter and intra parallelism)
        if tf_use == 'original':
            tf_command = "cd /home/Scheduler/models/ && logsave -a " + file_log_tf + " python3 "  +  algorithm + '.py ' + str(data["inter_parallelism"]) + ' ' +str(data["intra_parallelism"]) + ' ' + str(os.getpid())
            #tf_command = "cd /home/Scheduler/models/ && logsave -a " + file_log_tf + " python3 "  +  algorithm + '.py ' + str(6) + ' ' +str(1) + ' ' + str(os.getpid())
        else:
            # tf_command = "cd /home/Scheduler/models/ && " + 'python3 ' + algorithm + '.py ' + str(2) + ' ' + str(cores_cpu)  + ' ' +  str(os.getpid()) + ' > /home/Scheduler/models/output_' + str(threading.current_thread().ident) + '.txt'
            tf_command = "cd /home/Scheduler/models/ &&  logsave -a " + file_log_tf + ' python3 ' + algorithm + '.py ' + str(1) + ' ' + str(cores_cpu)  + ' ' +  str(os.getpid())
            # tf_command = "cd /home/Scheduler/models/ &&  logsave -a " + file_log_tf + ' python3 ' + algorithm + '.py ' + str(1) + ' ' + str(64)  + ' ' +  str(os.getpid())
            # tf_command = 'cd /home/Scheduler/models/ && python3 ' + algorithm + '.py ' + str(1) + ' ' + str(22)  + ' ' +  str(os.getpid()) + ' >> ' + file_log_tf + ' 2>&1'
        #tf_command = "cd /home/Scheduler/models/ && " + 'python3 hello_world.py > /home/Scheduler/models/output_' + str(threading.current_thread().ident) + '.txt'
        event_logs.save_event(1, 0, data["inter_parallelism"], data["intra_parallelism"])

        # Ejecutar comando TF
        logging.info('Execute TF algrithm in background...')
        tf_command_execute = Popen(tf_command, shell=True)
        #os.system(tf_command)
        
            # Enviar inicialización de TF al Scheduler
        logging.info('Send TF init message...')
        data2= {
            "status": 'init'
        }
        json_data_socket._send(socket_scheduler, data2)


        '''
        tf_command_execute = Popen(tf_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = tf_command_execute.communicate()
        if(stderr):
            #logging.info('Error en popen: ' + stderr)
        else:
            #logging.info('Salida de popen:' + stdout)
        '''
            
        # Esperar a que inicie correctamente el programa de TF
        time.sleep(2)

        event_logs.save_event(2, 0, 0)

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
        signal.signal(signal.SIGUSR1, partial(receiveSignal, socket_scheduler))

        # Crear hilo para la atención de solicitudes
        logging.info("Creating update attention thread...")
        update_thread = threading.Thread(target=attentionUpdate, args=(pid_tf,number_thread,data["inter_parallelism"],data["intra_parallelism"],))
        number_thread= number_thread+1

        # Crear hilo para la atención de solicitudes
        logging.info("Creating socket attention thread...")
        socket_thread = threading.Thread(target=attention_socket, args=(socket_scheduler,number_thread,))
        number_thread=number_thread+1

        # Crear hilo para la atención de solicitudes
        logging.info("Creating live thread...")
        live_thread = threading.Thread(target=live_control, args=(socket_scheduler,number_thread,file_log_tf))
        number_thread=number_thread+1

        # Ejecutar hilos
        update_thread.start()
        event_logs.add_thread()
        socket_thread.start()
        event_logs.add_thread()
        live_thread.start()
        event_logs.add_thread()

        # Hacer el join de los hilos
        logging.info("Join Threads...")
        update_thread.join()
        socket_thread.join()
        live_thread.join()
        
        logging.info("Save log in CSV format...")

        log_name= 'client_events_' + str(data["container"]) + '.txt'

        event_logs.save_CSV('/home/Scheduler/Data/log/',log_name)
        # Cerrar conexión del cliente con el scheduler
        logging.info("Close client socket")
        socket_scheduler.close()

        logging.info("Finish program :)")

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt")
    except BaseException as e:
        logging.info(repr(e))
        logging.info(traceback.format_exc())
        logging.info("Base error")
    except (SyntaxError, IndentationError, NameError) as err:
        logging.info(err)
    except socket_scheduler.error as err:
        logging.info(err)
        logging.info("Error in socket")
    except:
        logging.info("Unexpected error :(")