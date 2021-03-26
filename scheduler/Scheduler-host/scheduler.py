import os
import sys
import threading 
import random
import numpy as np
import queue
import time
from collections import namedtuple
from subprocess import Popen, PIPE, STDOUT
import signal
import socket
from execution_info import ExecutionInfo
from system import systemInfo
from scheduling_policy import FCFS
import copy
from Commons.trace import TraceLog
from Commons import events
from Commons import json_data_socket
from request import Start, Pause, Update, Resume, Finish
import csv

#Mutex para acceder al trace log
mutex_eventlogs= threading.Lock()
# Almacena la informacion de los eventos en el planificador
event_logs= TraceLog(1)

#Mutex para acceder al proximo numero de hilo
mutex_numberThread= threading.Lock()
# Numero de hilo que identifica unicamente a cada uno
number_thread=1

# Mutex para acceder con exclusión mutua a la información del sistema
mutex_systemInfo = threading.Lock()
# Encargada de manejar los recursos disponibles y utilizados en el sistema
system_info = systemInfo()

# Política de asignación de recursos a los contenedores (puede modificarse)
scheduler_container= FCFS("strict")

# Cola para almacenar peticiones de finalización de contenedor (almacena el paralelismo total liberado)
q_finish_container= queue.Queue(10)
# Cola para almacenar peticiones pendientes de atencion
q_request_pending= queue.Queue()
# Cola de hilos de clientes (usado para luego hacer el join de cada uno)
q_client_threads= queue.Queue()
# Almacena una variable condicion perteneciente a un cliente en particular
q_pause_containers= queue.Queue()

# Variable que indica si el hilo Atencion debe replanificar los hilos de los contenedores
rescheduling_containers= False

# Mutex para la lista de instancias TF en ejecución
mutex_execInfo= threading.Lock()
# Lista que almacena la información de cada instancia de TF que se encuentra en ejecución (puede tener instancias que ya terminaron)
execInfo_list=[]

# Mutex para lista de nombres de contenedores en ejecución
mutex_containerList= threading.Lock()
# Lista de nombres de contenedores en ejecución (para que el hilo update sepa a cuáles contenedores puede actualizar)
containerName_list=[]

# Variable condición utilizada para avisar al hilo Atencion de que hay pedidos pendientes en alguna cola.
cv_attention = threading.Condition()

mutex_finishExecution= threading.Lock()
finish_execution=False

# Metodos para manejo de señales #

def handler_finish(signum, frame):
    global finish_execution
    # Cambiar el valor de variable de finalizacion de planificador
    print("Signal finalize scheduler")
    mutex_finishExecution.acquire()
    finish_execution=True
    mutex_finishExecution.release()
    with cv_attention:
        cv_attention.notify()

# Fin de metodos para manejo de señales

# Métodos Generales #

# Bloquear execInfo_list y system_info antes de usarlo
def schedule_resources(request_, resources_availables):
    requested_resources=0
    if isinstance(request_, Pause):
        print ("Pause container request: ", request_.get_container_name())
        for x in execInfo_list:
                if x.get_container_name() == request_.get_container_name():
                    if x.get_state() != "pause":
                        instance_number= int(request_.get_container_name()[8])
                        x.pause_container()
                        mutex_eventlogs.acquire()
                        event_logs.save_event(events.PAUSE_CONTAINER, 0, instance_number)
                        event_logs.finish_container_event(instance_number)
                        event_logs.init_container_event(instance_number, 0)
                        mutex_eventlogs.release()
                        requested_resources= -(x.get_intra_exec_parallelism()+x.get_inter_exec_parallelism())
                        print("Resources to be released in pause: ", requested_resources)
    else:
        if isinstance(request_, Update):
            print("Update container request: ", request_.get_container_name())
            for x in execInfo_list:
                if x.get_container_name() == request_.get_container_name():
                    if x.get_state() == "start":
                        requested_resources= (request_.get_inter_parallelism()+request_.get_intra_parallelism()) - (x.get_inter_user_parallelism()+x.get_intra_user_parallelism())      
        else:
            if isinstance(request_, Resume):
                print("Resume container request: ", request_.get_container_name())
                for x in execInfo_list:
                    if x.get_container_name() == request_.get_container_name():
                        if x.get_state() != "start":
                            requested_resources= x.get_intra_exec_parallelism()+x.get_inter_exec_parallelism()
                            print("Requested resources in resume: ", requested_resources)
            else:
                # Obtener los recursos solicitados por la peticion de ejecucion 
                print("Execution container request: ", request_.get_container_name())
                requested_resources=request_.get_inter_parallelism()+request_.get_intra_parallelism()
        
    if ((requested_resources>0) and (requested_resources <= resources_availables)):
        # Reservar la cantidad de recursos disponibles 
        system_info.apply_resources(requested_resources)
    else:
        if(requested_resources>0): 
            # Quiere decir que es una peticion de incremento de recursos y no alcanza la cantidad recursos disponibles. Probar si la politica de planificacion acepta una peticion con esta cantidad de recursos.
            # Reservar la cantidad de recursos disponibles 
            system_info.apply_resources(resources_availables)
            requested_resources= resources_availables
        else:
            system_info.free_resources(-requested_resources)
            print("Free resources in parallelism reserve")
    return requested_resources

def schedule_request(request_, socket_schedule, instance_number=0, port_host=0, resources_availables=0, thread_id=0):

    global number_thread
    
    state=0

    if isinstance(request_, Start):

        # Atender peticion de actualizacion

        print('Schedule Execution Request: ',threading.current_thread().getName())

        parallelism_container= scheduler_container.schedule_parallelism(resources_availables, request_.get_inter_parallelism(), request_.get_intra_parallelism())

        # Accede a consultar si hay paralelismo disponible (system_info es thread-safe en este momento)
        if parallelism_container:
        
            container_name= 'instance' + str(instance_number)
            
            # Comando para iniciar contenedor con una imagen dada en la petición (opciones dit permiten dejar ejecutando el contenedor en background)
            print("Creating Docker Container...")

            docker_command= 'docker run -dit --name '+ container_name + ' -p ' + str(port_host) + ':8787 --volume $HOME/Documentos/gitlab/tensorflow/scheduler:/home/Scheduler ' + request_.get_image()
            
            # Ejecutar comando (con os.p)
            # Los primeros 12 caracteres de stdout son el container ID
            process_command = Popen([docker_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()

            if(len(stderr)):
                print(stderr)
            else:
                print(stdout)

            conn_established = False
            attemps = 0
            while (conn_established == False) and (attemps < 5):
                try:
                    # Establecer conexión con el contenedor cliente 
                    c, addr = socket_schedule.accept()
                    conn_established = True
                    # Crear hilo para la comunicación con el contenedor
                    tmp_thread = threading.Thread(target=container_client, args=(c,addr,container_name, instance_number, parallelism_container[0], parallelism_container[1],number_thread,))
                    tmp_thread.start()
                    event_logs.add_thread()
                    number_thread=number_thread+1
                    q_client_threads.put(tmp_thread)
                    mutex_numberThread.acquire()
                    number_thread=number_thread+1
                    mutex_numberThread.release()
                except socket.timeout:
                    print("Connection establish timeout")
                    attemps= attemps+1
                    if attemps == 5:
                        print("Could not create docker container")
                    pass
            
            if attemps != 5:

                mutex_eventlogs.acquire()
                event_logs.save_event(events.ATTENTION_REQUEST_EXE, thread_id, instance_number, parallelism_container[0]+parallelism_container[1])
                event_logs.init_container_event(instance_number, parallelism_container[0]+parallelism_container[1])
                mutex_eventlogs.release()

                #Transformar stdout en container ID
                container_id =  stdout[:12]
                
                # almacenar ID del proceso
                process_id_command= 'docker container top ' + container_id + ' -o pid'
                process_command = Popen([process_id_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                stdout, stderr = process_command.communicate()

                #Transformar la salida de stdout en process ID 
                # Salida de ejemplo:
                # PID
                # 4483   
                # Me quedo con la parte de abajo de la salida (si tiene hasta 4 dígitos el PID, sino ver cómo solucionar)
                process_id = stdout[4:8] 

                if(len(stderr)):
                    print(stderr)
                else:
                    print('Name of request: ', container_name, ' - Container ID: ', container_id, 'Container Process ID: ', process_id)

                # Crear un ExecutionInfo para almacenar la informacion de la instancia ejecutada
                exec_info = ExecutionInfo(container_name, instance_number, port_host, process_id, request_.get_inter_parallelism(), request_.get_intra_parallelism(), parallelism_container[0], parallelism_container[1], c)

                # Almacenar instancia de execución en la lista de ejecuciones activas (es thread safe)
                mutex_execInfo.acquire()
                execInfo_list.append(exec_info)
                mutex_execInfo.release()

                # Almacenar nombre del contenedor para que en el update pueda actualizarlos 
                mutex_containerList.acquire()
                containerName_list.append(container_name)
                mutex_containerList.release()
                state=1
    else:
        container_number= int(request_.get_container_name()[8])
        if isinstance(request_, Update):
            # Atender petición de actualización
            print('Schedule Update Request: ',threading.current_thread().getName(), ' - Container: ', container_number)
            # Obtener objeto ExecutionInfo correspondiente a la instancia que se desea actualizar 
            ok, parallelism_apply = updateExecutionInstance(request_.get_container_name(), request_.get_inter_parallelism(), request_.get_intra_parallelism(), resources_availables)
            if(ok):
                print("Container: ",container_number," updated successfully")
                mutex_eventlogs.acquire()
                event_logs.save_event(events.ATTENTION_REQUEST_UP, thread_id, container_number, request_.get_intra_parallelism()+request_.get_inter_parallelism())
                event_logs.finish_container_event(container_number)
                event_logs.init_container_event(container_number,parallelism_apply)
                mutex_eventlogs.release()
                state=1  
            else:
                print("Container is not running (abort update)")
        else:      
            print("Schedule Resume Request: ", threading.current_thread().getName(), ' - Container: ', container_number)
            mutex_execInfo.acquire()
            for container_info in execInfo_list:
                if (container_info.get_container_name() == request_.get_container_name()):      
                    parallelism_container= scheduler_container.schedule_parallelism(resources_availables, container_info.get_inter_exec_parallelism(), container_info.get_intra_exec_parallelism())   
                    if parallelism_container:
                        # Asignar paralelismo al contenedor
                        container_info.set_inter_exec_parallelism(parallelism_container[0])
                        container_info.set_intra_exec_parallelism(parallelism_container[1])
                        # Reanudar ejecucion del contenedor
                        print("Execute resume container...")
                        container_info.resume_container()
                        # Despertar al hilo cliente para que escuche mensajes
                        container_info.signal_execution()
                        # Almacenar evento
                        mutex_eventlogs.acquire()
                        event_logs.finish_container_event(container_number)
                        event_logs.init_container_event(container_number,parallelism_container[0]+parallelism_container[1])
                        mutex_eventlogs.release()
                        state=1 
            mutex_execInfo.release()                 
    return state

def updateExecutionInstance(container_name, new_inter_parallelism, new_intra_parallelism, resources_availables):
    
    parallelism_apply= 0
    
    # Buscar en la lista execInfo_list la instancia de ejecucion perteneciente al contenedor con nombre container_name y actualizar el paralelismo
    # En este momento system_info es thread-safe (desde attentionRequest)  
    ok=False
    mutex_execInfo.acquire()
    for x in execInfo_list:
        if x.get_container_name() == container_name:
            if (x.get_state() != "start"):
                ok= False    
            else:
                # Obtener los paralelismos de ejecucion del contenedor
                old_interParallelism= x.get_inter_exec_parallelism()
                old_intraParallelism= x.get_intra_exec_parallelism()

                print('Old Parallelism: Inter=', old_interParallelism, ' - Intra=', old_intraParallelism, ' New Parallelism: Inter=', new_inter_parallelism, ' - Intra=', new_intra_parallelism)

                # Si es menor a cero quiere decir que vamos a decrementar el paralelismo total del contenedor
                if resources_availables<0:
                    ok = x.update_parallelism(new_inter_parallelism, new_intra_parallelism)
                    parallelism_apply= new_inter_parallelism + new_intra_parallelism
                    print("Free resources in container reassigment")
                    ok=True
                else:
                    parallelism_list= scheduler_container.schedule_parallelism(resources_availables, new_inter_parallelism-old_interParallelism, new_intra_parallelism-old_intraParallelism)
                    if parallelism_list:
                        print("Parallelism Apply: ", parallelism_list[0] + parallelism_list[1])
                        ok = x.update_parallelism(old_interParallelism+parallelism_list[0] , old_intraParallelism+parallelism_list[1])
                        parallelism_apply= old_interParallelism + parallelism_list[0] + old_intraParallelism + parallelism_list[1]
                        if(new_inter_parallelism-old_interParallelism < 0):
                            print("Increment intra parallelism and decrement inter parallelism")
                        else:
                            if(new_intra_parallelism-old_intraParallelism < 0):
                                print("Increment inter parallelism and decrement intra parallelism")
                            else:
                                print("Increment both parallelisms")
                        ok=True
                    else:
                        ok=False
    mutex_execInfo.release()
    
    return ok, parallelism_apply

# System Info Safe
def oldest_reassigment(resources_availables, increase_or_reduce, amount_reduce=0, thread_id=0):

    print("Reassigment Containers with oldest policy")

    mutex_eventlogs.acquire()
    event_logs.save_event(events.REASSIGMENT_RESOURCES,thread_id,-1)
    mutex_eventlogs.release()

    if increase_or_reduce:
        mutex_execInfo.acquire()
        for container in execInfo_list:
            ok=False
            interUser_parallelism= container.get_inter_user_parallelism()
            intraUser_parallelism= container.get_intra_user_parallelism()
            interparallelism_required= interUser_parallelism -  container.get_inter_exec_parallelism()
            intraparallelism_required= intraUser_parallelism -  container.get_intra_exec_parallelism()
            if resources_availables >0:
                # Aumentar todo el paralelismo al contenedor
                if (interparallelism_required>0 and intraparallelism_required>0):
                    if resources_availables >= (interparallelism_required + intraparallelism_required):             
                        container.update_parallelism(interUser_parallelism, intraUser_parallelism)
                        print("Update total parallelism in container: ", container.get_container_name())
                        resources_availables= resources_availables-interparallelism_required-intraparallelism_required                       
                    else:
                        # Aumentar solo el intra paralelismo
                        if (resources_availables >= intraparallelism_required):
                            container.update_parallelism(intra_parallelism=intraUser_parallelism+intraparallelism_required)
                            resources_availables= resources_availables - intraparallelism_required
                            print("Update total intra parallelism in container: ", container.get_container_name(), " to: ", intraparallelism_required)
                        else:
                            container.update_parallelism(intra_parallelism=intraUser_parallelism+resources_availables) 
                            resources_availables=0
                            print("Update intra parallelism in container: ", container.get_container_name(), "to: ", intraUser_parallelism+resources_availables)
                        # Intentar aumentar el inter paralelismo con los recursos disponibles restantes (si es que hay)
                        if (resources_availables>0):
                            container.update_parallelism(inter_parallelism=interUser_parallelism+resources_availables)
                            resources_availables=0 
                            print("Update inter parallelism in container: ", container.get_container_name(), "to: ", interUser_parallelism+resources_availables)
                    ok=True
                else:
                    if(intraparallelism_required>0):
                        if (resources_availables >= intraparallelism_required):
                            container.update_parallelism(intra_parallelism=intraUser_parallelism+intraparallelism_required)
                            resources_availables= resources_availables - intraparallelism_required
                            print("Update total intra parallelism in container: ", container.get_container_name(), " to: ", intraparallelism_required)
                        else:
                            container.update_parallelism(intra_parallelism=intraUser_parallelism+resources_availables) 
                            resources_availables=0
                            print("Update intra parallelism in container: ", container.get_container_name(), "to: ", intraUser_parallelism+resources_availables)
                        ok=True
                    else:
                        if(interparallelism_required>0):
                            if (resources_availables >= interparallelism_required):
                                container.update_parallelism(inter_parallelism=interUser_parallelism+interparallelism_required)
                                resources_availables= resources_availables - interparallelism_required
                                print("Update total inter parallelism in container: ", container.get_container_name(), " to: ", interparallelism_required)
                            else:
                                container.update_parallelism(inter_parallelism=interUser_parallelism+resources_availables) 
                                resources_availables=0
                                print("Update inter parallelism in container: ", container.get_container_name(), "to: ", interUser_parallelism+resources_availables)
                            ok=True
            if ok:
                mutex_eventlogs.acquire()
                event_logs.save_event(events.REASSIGMENT_RESOURCES, thread_id, container.getContainerNumber(), container.get_inter_exec_parallelism()+container.get_intra_exec_parallelism())
                mutex_eventlogs.release()
            if resources_availables == 0:
                break
        mutex_execInfo.release()
    else:
        # reducir el paralelismo de los contenedores mas viejo liberando la cantidad de recursos solicitados (amount_reduce)
        pass

    return resources_availables

# Fin Métodos Generales #

# Métodos asignados a hilos #

def generatePauseResumeRequest(thread_id):
    print('PauseResumeRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)    

    mutex_finishExecution.acquire()
    while not finish_execution:  
        skip=False
        mutex_finishExecution.release()
        # Tiempo de espera para la próxima petición
        # Se utiliza distribución normal de tiempo con medio en 40 segundos y desviación estándar de 10 segundos
        normal_time = np.random.normal(loc=60, scale=10, size=1)
        time_wait= int(normal_time[0])   
        time.sleep(time_wait)     
        mutex_containerList.acquire()
        try:
            container_name = random.choice(containerName_list)
        except: 
            print("Container not exist in List")
            skip=True
        mutex_containerList.release()     
        if not skip:       
            request_ = Pause(container_name)
            scheduler_container.add_new_request(request_)
            print("Schedule Pause request to container: ", container_name)
            # Avisar al hilo de atencion que se encoló una nueva petición.
            with cv_attention:
                cv_attention.notify()
                #print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)
                
            time_wait= int(normal_time[0])  
            time.sleep(time_wait)
            request_ = Resume(container_name)
            scheduler_container.add_new_request(request_)   
            print("Schedule Resume request to container: ", container_name)  
            # Avisar al hilo de atencion que se encoló una nueva petición.
            with cv_attention:
                cv_attention.notify()
                #print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)              
        mutex_finishExecution.acquire()
    mutex_finishExecution.release()
    print("Finish Pause-Resume request thread")
    
def read_requests(thread_id):
    
    with open('./Scheduler-host/requests_file.txt') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        cant_request = 0
        for row in csv_reader:
            cant_request+=1
            if (row[0]=='execution'):
                request_exec = Start("", row[2],int(row[3]),int(row[4]))
                scheduler_container.add_new_request(request_exec)   
                mutex_eventlogs.acquire()
                event_logs.save_event(events.GENERATE_REQUEST_EXE, thread_id, request_exec.get_inter_parallelism()+request_exec.get_intra_parallelism())
                event_logs.init_container_event(-1, int(row[3])+int(row[4]))
                time.sleep(1)
                event_logs.finish_container_event(-1)
                mutex_eventlogs.release()   
            else:
                request_up= Update(row[1], int(row[3]), int(row[4]))
                scheduler_container.add_new_request(request_up)
                mutex_eventlogs.acquire()
                event_logs.save_event(events.GENERATE_REQUEST_EXE, thread_id, request_exec.get_inter_parallelism()+request_exec.get_intra_parallelism())
                event_logs.init_container_event(-2, int(row[3])+int(row[4]))
                time.sleep(1)
                event_logs.finish_container_event(-2)
                mutex_eventlogs.release()  
                pass
            with cv_attention:
                cv_attention.notify()
            time.sleep(int(row[5]))
    
    print("Finish read request thread, request count= ", cant_request)

def container_client(clientsocket,addr,container_name, instance_number, interExec_parallelism, intraExec_parallelism, thread_id):
    container_eliminated= False
    data= {
        "container": instance_number,
        "inter_parallelism": interExec_parallelism,
        "intra_parallelism": intraExec_parallelism
    }
    json_data_socket._send(clientsocket, data)
    msg=''
    loop=0
    # Esperar mensaje de finalización. 
    while not container_eliminated:
        try:
            # Recibir mensaje de finalización o problema del contenedor
            msg= json_data_socket._recv(clientsocket)
            if loop==0:
                print('Message recieved from Client ID: '+ str(instance_number)+" - Message: "+ msg["status"])
            loop=loop+1
            #print (container_name, "send message: ", msg) (ver por qué recibe tantos mensajes vacios)
            if msg["status"] == 'exit':
                mutex_eventlogs.acquire()
                event_logs.save_event(events.FINISH_CONTAINER, thread_id, instance_number)
                event_logs.finish_container_event(instance_number)
                mutex_eventlogs.release()
                 # Buscar contenedor en la lista
                # Eliminar objeto contenedor de la lista de contenedores activos
                mutex_execInfo.acquire()
                for elem in execInfo_list:
                    if (elem.container_name == container_name):         
                        # Encolar paralelismo liberado por el contenedor
                        q_finish_container.put(elem.get_inter_exec_parallelism() + elem.get_intra_exec_parallelism())
                        print("Push Free Parallelism of Container: ", container_name, " Parallelism: ", elem.get_inter_exec_parallelism() + elem.get_intra_exec_parallelism())
                        #Despertar al hilo de atencion
                        with cv_attention:
                            cv_attention.notify()
                            print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)       
                        execInfo_list.remove(elem)
                        print('Eliminate Container ', container_name, ' because it finished')
                        container_eliminated= True
                        break
                mutex_execInfo.release()
                # Eliminar el nombre de la lista de contenedores activos para que no se generen nuevas peticiones de actualización
                mutex_containerList.acquire()
                print("Remove container from container list")
                containerName_list.remove(container_name)
                mutex_containerList.release()
                # Informar en caso de que no se pueda eliminar el contenedor
                if not container_eliminated:
                    print('The container ', container_name, ' could not be deleted')
                else: 
                    # Enviar ACK indicando finalizacion de la eliminacion del cliente
                    print("Send ACK to client: " + str(instance_number))
                    data={
                        "container": instance_number,
                        "inter_parallelism": -1,
                        "intra_parallelism": -1
                    }
                    json_data_socket._send(clientsocket, data)
        except socket.timeout: # fail after 60 second of no activity
            print("Didn't receive data! [Timeout] - Container: " + str(instance_number))
        except socket.error as ex: 
            print("Connection reset by peer with request count=" + str(loop))
            print(ex)
        finally:
            print("Check if container has paused...")
            paused=False
            mutex_execInfo.acquire()
            for elem in execInfo_list:
                if (elem.container_name == container_name):
                    if(elem.get_state() == "pause"):
                        mutex_execInfo.release()
                        paused=True
                        elem.wait_execution()
            if not paused:
                mutex_execInfo.release()
    #Esperar a que finalice el contenedor
    time.sleep(10)
    # Eliminar contenedor pausado (docker container prune)
    command= "docker container prune -f"
    eliminate_container = Popen(command, shell=True)
    print("Finish Client Thread - Container: ", instance_number)

def attentionRequest(socket_schedule, thread_id):
    print('AttentionRequest Thread:', threading.current_thread().getName())
    instance_number=0
    request_pending=False
    port_host=8787
    global q_request_pending
    global finish_execution
    mutex_finishExecution.acquire()
    while not finish_execution: # esto tenerlo en cuenta para vaciar colas de peticiones pero no como condicion de corte
        mutex_finishExecution.release()
        with cv_attention:
            # Esperar a que alguno de los demas hilos avise que hay peticiones pendientes (ejecución, actualización o eliminación de contenedores)
            cv_attention.wait()
            #print('Wake up:', threading.current_thread().getName())
        if not q_finish_container.empty():
            
            print('Attention finish request: ',threading.current_thread().getName())
            # Atender peticiones de finalización de contenedores
            while not q_finish_container.empty():
                parallelism_free= q_finish_container.get()
                mutex_systemInfo.acquire()
                system_info.free_resources(parallelism_free)
                mutex_systemInfo.release()

            print('Reassigment free parallelism: ',threading.current_thread().getName())
            # reasigno contenedores con prioridad de los contenedores mas viejos (indicando que se aumenten sus recursos asignados)
            mutex_systemInfo.acquire()
            resources_availables= system_info.check_resources()
            print("Free Resources for Reassigment: ", resources_availables)    
            if resources_availables>0: 
                system_info.apply_resources(resources_availables)
                mutex_systemInfo.release()
                resources_availables= oldest_reassigment(resources_availables, True, thread_id)
                if resources_availables > 0:
                    mutex_systemInfo.acquire()
                    system_info.free_resources(resources_availables)
                    mutex_systemInfo.release()

        print('Attention act/exe request pending: ',threading.current_thread().getName())
        # Intentar atender las peticiones pendientes de ejecucion/actualizacion
        mutex_systemInfo.acquire()
        resources_availables= system_info.check_resources()
        q_aux= queue.Queue()
        request_= scheduler_container.get_pending_request()
        while ((resources_availables>0) and (request_)):
            requested_resources = schedule_resources(request_, resources_availables)
            if (requested_resources!=0):
                # Intentar planificar peticion pendiente    
                mutex_systemInfo.release()   
                state= schedule_request(request_, socket_schedule, instance_number, port_host, requested_resources, thread_id)
                mutex_systemInfo.acquire()  
                # Verificar estado de la planificacion de peticion        
                if state==0:
                    print ("Pending petition could not be answered")
                    q_aux.put(request_)
                    system_info.free_resources(requested_resources)
                else:
                    if isinstance(request_, Start):
                        instance_number=instance_number+1
                        port_host= port_host+1   
                resources_availables= system_info.check_resources()
                print("Resources availables after schedule: " + str(resources_availables))
            request_ = scheduler_container.get_pending_request()
        mutex_systemInfo.release()
        # Almacenar las peticiones antiguas pendientes en la cola nuevamente
        while (not q_aux.empty()):
           scheduler_container.add_pending_request(q_aux.get())
                
        print('Attention new act/exe request: ',threading.current_thread().getName())
        # Intentar atender nuevas peticiones de ejecucion/actualizacion
        mutex_systemInfo.acquire()
        resources_availables= system_info.check_resources()
        finish_schedule_queue=False
        request_= scheduler_container.get_new_request()
        while ((resources_availables > 0) and (request_)):
            requested_resources = schedule_resources(request_, resources_availables)            
            mutex_systemInfo.release()
            # Borrar luego #
            if isinstance(request_, Update):
                print('Update Request: ', request_.get_container_name(), ' Inter-Parallelism:', request_.get_inter_parallelism(), ' Intra-Parallelism:', request_.get_intra_parallelism(), ' Thread-ID:', threading.current_thread().getName())  
            else:
                if isinstance(request_, Start):
                    print('Schedule request - Inter-Parallelism:', request_.get_inter_parallelism(), ' Intra-Parallelism:', request_.get_intra_parallelism(), ' Thread-ID:', threading.current_thread().getName())  
            ################
            if ((not isinstance(request_, Pause)) and (requested_resources!=0)):
                state= schedule_request(request_, socket_schedule, instance_number, port_host, requested_resources, thread_id)  
                # Verificar si no se pudo atender la peticion
                if (state==0):
                    if isinstance(request_, Resume):
                        print("Resume request pending")
                        scheduler_container.add_pending_request(request_)
                    else:
                        # Verificar si la cantidad de paralelismo solicitada excede el máximo de la máquina
                        if((request_.get_inter_parallelism()+request_.get_intra_parallelism())>system_info.total_cores()):
                            print("Request discarded because the parallelism requested exceeds the maximum number of cores of the machine")
                        else:
                            print("New request pending")
                            scheduler_container.add_pending_request(request_)
                    system_info.free_resources(requested_resources)
                else: 
                    if isinstance(request_, Start):
                        instance_number=instance_number+1
                        port_host= port_host+1   
            else:
                if not isinstance(request_, Pause):
                    print("Discard this request") 
            mutex_systemInfo.acquire()
            resources_availables= system_info.check_resources()
            print("Resources availables after schedule: " + str(resources_availables)) 
            request_= scheduler_container.get_new_request()  
        mutex_systemInfo.release() 
        mutex_finishExecution.acquire()
    mutex_finishExecution.release()
    
    print (" Attention pending resumes...")
    # Contabilizar la cantidad de resume pendientes
    mutex_execInfo.acquire()
    for container_info in execInfo_list:
        if container_info.get_state() == "pause":
            mutex_execInfo.release()
            complete= False
            request_= Resume(container_info.get_container_name())
            while not complete:
                with cv_attention:
                    # Esperar a que los contenedores que finalicen me despierten
                    print("Espero finalizacion de un contenedor...")
                    cv_attention.wait()  
                mutex_systemInfo.acquire()   
                while not q_finish_container.empty():
                    parallelism_free= q_finish_container.get()
                    print("Free resources count: ", parallelism_free)
                    system_info.free_resources(parallelism_free) 
                resources_availables= system_info.check_resources()
                requested_resources = schedule_resources(request_, resources_availables) 
                mutex_systemInfo.release() 
                if requested_resources >0:
                    state= schedule_request(request_, socket_schedule, instance_number, port_host, requested_resources, thread_id)     
                    if state != 0:
                        complete=True
                    else: 
                        mutex_systemInfo.acquire()  
                        system_info.free_resources(resources_availables)
                        mutex_systemInfo.release()
            mutex_execInfo.acquire()           
    mutex_execInfo.release()
    
    print("Finish attention thread")

# Programa Principal #
if __name__ == "__main__":

    print("Scheduler for Instances TF")

    print("Connecting Network...")

    '''
    # Obtener Ip de la red docker
    network_command= Popen(["docker network inspect schedule-net --format {{.IPAM.Config}}"], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    stdout, stderr = network_command.communicate()

    if (len(stderr)):
        print(stderr)
    else:
        print("IP of network docker: ", stdout[2:12])
        network_ip= stdout[2:12]
        port=65000
    '''

    # Definir time out de espera a que le responda el cliente
    socket.setdefaulttimeout(60)

    # Definir socket servidor
    socket_schedule= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_schedule.bind(('172.17.0.1', 65000))
    socket_schedule.listen()

    print("Add ctl+z signal handler...")
    signal.signal(signal.SIGTSTP, handler_finish)

    print("Creating threads...")
    # Crear hilo para la atención de solicitudes
    attention_thread = threading.Thread(target=attentionRequest, args=(socket_schedule,number_thread,))
    event_logs.add_thread()
    number_thread= number_thread+1

    # Crear hilo para la generacion de peticiones de ejecución
    request_thread = threading.Thread(target=read_requests, args=(number_thread,))
    event_logs.add_thread()
    number_thread=number_thread+1
    
    # Iniciar todos los hilos
    attention_thread.start()
    request_thread.start()
    
    # Esperar la terminación de los hilos
    attention_thread.join()
    request_thread.join()

    # Esperar la terminacion de los hilos clientes
    print("Join client threads...")
    while not q_client_threads.empty():
        client= q_client_threads.get()
        client.join()

    socket_schedule.close()

    print("Save data log...")
    event_logs.save_CSV('./Data/log/', 'scheduler_events.txt')
    print("Print data events...")
    event_logs.plot_events()
    event_logs.plot_gantt()
# Fin de Programa Principal #