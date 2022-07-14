from email import policy
import os
from sqlite3 import Time
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
from scheduling_policy import FCFS, Priority
import copy
from Commons.trace import TraceLog
from Commons.time_epochs import TimeEpochs
from Commons import events
from Commons import json_data_socket
from request import Start, Pause, Update, Resume, Finish, Restart
import csv
import json
import psutil

#Mutex para acceder al proximo numero de hilo
mutex_numberThread= threading.Lock()
# Numero de hilo que identifica unicamente a cada uno
number_thread=1

# Mutex para acceder con exclusión mutua a la información del sistema
mutex_systemInfo = threading.Lock()
# Encargada de manejar los recursos disponibles y utilizados en el sistema
system_info = systemInfo()

# Política de asignación de recursos a los contenedores (puede modificarse)
scheduler_container= ''
# scheduler_container= FCFS("strict")
# scheduler_container= FCFS("always_attend")
# scheduler_container= FCFS("max_prop")

#Mutex para acceder al trace log
mutex_eventlogs= threading.Lock()
# Almacena la informacion de los eventos en el planificador
event_logs= ""

# Cola para almacenar peticiones de finalización de contenedor (almacena el paralelismo total liberado)
q_finish_container= queue.Queue()
# Cola de hilos de clientes (usado para luego hacer el join de cada uno)
#q_client_threads= queue.Queue()
dict_client_threads={}
mutex_dict_client_threads= threading.Lock()
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

# Utilizado en la reasignacion max_prop
scheduling_requests= threading.Lock()

# Variable condición utilizada para avisar al hilo Atencion de que hay pedidos pendientes en alguna cola.
cv_attention = threading.Condition()

mutex_finishExecution= threading.Lock()
finish_execution=False

tf_version=""

creation_requests_terminate= False

# Contabiliza la cantidad de contenedores que fallan y deben reiniciarse
containers_failed=0
mutex_containersFailed= threading.Lock()

# Control of assigmented resources
not_control=False

# Enable or Disable reassigment resources option
reassigment=True

# Enable when resources are released if first reallocate or Disable if use them for new containers
priority_reassigment=True

global_resources_ok= True

# Metodos para manejo de señales #

def handler_finish(signum, frame):
    global finish_execution
    # Cambiar el valor de variable de finalizacion de planificador
    # print("Signal finalize scheduler")
    mutex_finishExecution.acquire()
    finish_execution=True
    mutex_finishExecution.release()
    with cv_attention:
        cv_attention.notify()

# Fin de metodos para manejo de señales

# Consultar si las colas están vacias y el hilo generador de peticiones terminó 
def is_finish_attention():
    global creation_requests_terminate
    global finish_execution
    mutex_containerList.acquire()
    # print("Container list: " , containerName_list)
    # print("Creatrion request:", creation_requests_terminate)
    # print("Pending queue: ", scheduler_container.pending_queue_empty())
    # print("Queue: ",scheduler_container.queue_empty())
    if (scheduler_container.pending_queue_empty() == -1) and (scheduler_container.queue_empty() == -1) and (creation_requests_terminate==True) and (not containerName_list) :
        mutex_finishExecution.acquire()
        finish_execution=True 
        mutex_finishExecution.release()
        mutex_containerList.release()
        return True
    else: 
        mutex_containerList.release()
        return False

# Métodos Generales #

# Bloquear execInfo_list y system_info antes de usarlo
def schedule_resources(request_, resources_availables):
    log_file= False
    global not_control
    requested_resources=0
    if isinstance(request_, Pause):
        print ("Pause container request: ", request_.get_request_id()) if log_file else None 
        for x in execInfo_list:
                if x.get_request_id() == request_.get_request_id():
                    if x.get_state() != "pause":
                        instance_number= x.get_containerNumber()
                        x.pause_container()
                        #filename_epochs= "models/output_" + str(instance_number) + "_" + tf_version + ".txt"
                        #time_epochs= TimeEpochs().process_TF_file(filename_epochs)
                        mutex_eventlogs.acquire()
                        event_logs.save_event(events.PAUSE_CONTAINER, 0, instance_number)
                        event_logs.finish_container_event(instance_number, [])
                        event_logs.init_container_event(instance_number, 0, instance_number)
                        mutex_eventlogs.release()
                        requested_resources= -(x.get_intra_exec_parallelism()+x.get_inter_exec_parallelism())
                        print("Resources to be released in pause: ", requested_resources)
    else:
        if isinstance(request_, Update):
            print("Update container request: ", request_.get_request_id()) if log_file else None 
            for x in execInfo_list:
                name_request= 'instance'+str(request_.get_request_id())
                if x.get_request_id() == name_request:
                    if x.get_state() == "start":
                        requested_resources= (request_.get_inter_parallelism()+request_.get_intra_parallelism()) - (x.get_inter_exec_parallelism()+x.get_intra_exec_parallelism())      
                        print("Requested_resources in update: ", requested_resources) if log_file else None 
        else:
            if isinstance(request_, Resume):
                print("Resume container request: ", request_.get_request_id()) if log_file else None 
                for x in execInfo_list:
                    if x.get_request_id == request_.get_request_id():
                        if x.get_state() != "start":
                            requested_resources= x.get_intra_exec_parallelism()+x.get_inter_exec_parallelism()
                            print("Requested resources in resume: ", requested_resources) if log_file else None 
            else:
                if isinstance(request_, Start):
                    # Obtener los recursos solicitados por la peticion de ejecucion 
                    print("Execution container request: ", request_.get_request_id()) if log_file else None 
                    requested_resources=request_.get_inter_parallelism()+request_.get_intra_parallelism()
                else: 
                    # Obtener los recursos del contenedor a partir de la lista de contenedores
                    container_name= request_.get_container_name()
                    for elem in execInfo_list:
                        if (elem.get_container_name() == container_name):         
                            # Encolar paralelismo liberado por el contenedor
                            requested_resources= elem.get_inter_exec_parallelism() + elem.get_intra_exec_parallelism()    
    if (not_control):
        system_info.apply_resources(requested_resources, not_control)
    else:
        if ((requested_resources>0) and (requested_resources <= resources_availables)):
            if scheduler_container.get_reassigment_type()=="max_prop":
                system_info.apply_resources(resources_availables, not_control)
                requested_resources= resources_availables
            else:
                # Reservar la cantidad de recursos disponibles 
                system_info.apply_resources(requested_resources, not_control)
        else:
            if(requested_resources>0): 
                # Quiere decir que es una peticion de incremento de recursos y no alcanza la cantidad recursos disponibles. Probar si la politica de planificacion acepta una peticion con esta cantidad de recursos.
                # Reservar la cantidad de recursos disponibles 
                system_info.apply_resources(resources_availables, not_control)
                requested_resources= resources_availables
            else:
                system_info.free_resources(-requested_resources)
                print("Free resources in parallelism reserve") if log_file else None 
    return requested_resources

def schedule_request(request_, socket_schedule, port_host=0, resources_availables=0, thread_id=0):
    log_file=True
    global number_thread   
    state=0
    parallelism_apply=0
    parallelism_container= [0,0]
    instance_number= request_.get_request_id()
    if isinstance(request_, Start) or isinstance(request_, Restart):
        # Atender peticion de actualizacion      
        if not_control:
            parallelism_container[0]= request_.get_inter_parallelism()
            parallelism_container[1]= request_.get_intra_parallelism()
        else:    
            print('Request inter parallelism: ', request_.get_inter_parallelism(), ' - Request intra parallelism: ', request_.get_intra_parallelism()) if log_file else None 
            parallelism_container= scheduler_container.schedule_parallelism(resources_availables, request_.get_inter_parallelism(), request_.get_intra_parallelism())
        # Accede a consultar si hay paralelismo disponible (system_info es thread-safe en este momento)
        if ((parallelism_container) and (system_info.memory_usage() < 80.0)):
            parallelism_apply= parallelism_container[0]+parallelism_container[1]
            if isinstance(request_, Start):
                container_name= 'instance' + str(instance_number)
            else:
                container_name= request_.get_container_name()
            # Comando para iniciar contenedor con una imagen dada en la petición (opciones dit permiten dejar ejecutando el contenedor en background)
            print("Creating Docker Container for " , container_name) if log_file else None 
            ok_start= False
            while(not ok_start):
                docker_command= 'docker run -dit --cpus=' + str(parallelism_apply) + ' --name '+ container_name + ' -p ' + str(port_host) + ':8787 --volume $HOME/scheduler:/home/Scheduler ' + request_.get_image()
                # Ejecutar comando (con os.p)
                # Los primeros 12 caracteres de stdout son el Execution container request:container ID
                process_command = Popen([docker_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                stdout, stderr = process_command.communicate()
                if(len(stderr)):
                    print(stderr) if log_file else None 
                    print("Stop container because not start: instance ", str(instance_number)) if log_file else None 
                    docker_command= 'docker container stop instance' + str(instance_number) + ' && docker container prune -f'
                    process_command = Popen(docker_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                    stdout, stderr = process_command.communicate()
                    sys.exit(1)
                else:
                    print(stdout) if log_file else None 
                    ok_start=True
            conn_established = False
            attemps = 0
            while (conn_established == False) and (attemps < 5):
                try:
                    # Establecer conexión con el contenedor cliente 
                    c, addr = socket_schedule.accept()
                    conn_established = True
                    if isinstance(request_, Start):
                        # Crear hilo para la comunicación con el contenedor
                        tmp_thread = threading.Thread(target=container_client, args=(c,addr,container_name, instance_number, parallelism_container[0], parallelism_container[1],number_thread,request_,False,))
                    else:
                        # Crear hilo para la comunicación con el contenedor reiniciado
                        tmp_thread = threading.Thread(target=container_client, args=(c,addr,container_name, instance_number, parallelism_container[0], parallelism_container[1],number_thread,request_,True,))
                    tmp_thread.start()
                    event_logs.add_thread()
                    number_thread=number_thread+1
                    # Almacenar hilo en diccionario 
                    mutex_dict_client_threads.acquire()
                    dict_client_threads [container_name] = tmp_thread
                    mutex_dict_client_threads.release()
                    #q_client_threads.put(tmp_thread)
                    mutex_numberThread.acquire()
                    number_thread=number_thread+1
                    mutex_numberThread.release()
                except socket.timeout:
                    print("Connection establish timeout - Container: instance", str(instance_number))
                    attemps= attemps+1
                    if attemps == 5:
                        print("Could not create docker container - Container: instance", str(instance_number))
                    pass
                except BaseException:
                    print("Unexpected error in socket connection")     
            if attemps != 5:
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
                    print(stderr) if log_file else None 
                else:
                    print('Name of request: ', container_name, ' - Container ID: ', container_id, 'Container Process ID: ', process_id) if log_file else None 
                if isinstance(request_, Restart):
                    # Actualizar informacion del contenedor reiniciado
                     for elem in execInfo_list:
                        if (elem.get_container_name() == container_name):         
                           elem.update_info(process_id, parallelism_container[0], parallelism_container[1], port_host, c, 'start')
                else:
                    # Crear un ExecutionInfo para almacenar la informacion de la instancia ejecutada
                    exec_info = ExecutionInfo(container_name, instance_number, port_host, process_id, request_.get_inter_parallelism(), request_.get_intra_parallelism(), parallelism_container[0], parallelism_container[1], c, request_.get_image(), request_.get_priority())
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
        # Buscar numero de contenedor
        container_name=''
        for container_info in execInfo_list:
            instance_name= 'instance'+request_.get_request_id()
            if (container_info.container_name() == instance_name):
                container_number= container_info.get_container_number()
                container_name= container_info.get_container_name()
                container_intra_parallelism= container_info.get_intra_exec_parallelism()
                container_inter_parallelism= container_info.get_inter_exec_parallelism()
                break
        if(container_name != ''):
            if isinstance(request_, Update):
                # Atender petición de actualización
                print('Schedule Update Request: ',threading.current_thread().getName(), ' - Container: ', container_number, ' - Resources availables: ' , resources_availables) if log_file else None 
                # Obtener objeto ExecutionInfo correspondiente a la instancia que se desea actualizar 
                ok, parallelism_apply = updateExecutionInstance(container_name, request_.get_inter_parallelism(), request_.get_intra_parallelism(), resources_availables)
                if(ok):
                    print("Container: ",container_number," updated successfully") if log_file else None 
                    #filename_epochs= "models/output_" + str(container_number)+ "_"  + tf_version + ".txt"
                    #time_epochs= TimeEpochs().process_TF_file(filename_epochs)
                    mutex_eventlogs.acquire()
                    event_logs.save_event(events.ATTENTION_REQUEST_UP, request_.get_request_id(), intra_exec=request_.get_intra_parallelism(), inter_exec=request_.get_inter_parallelism())
                    event_logs.finish_container_event(container_number, [])
                    event_logs.init_container_event(container_number,(parallelism_apply+container_inter_parallelism+container_intra_parallelism), instance_number)
                    mutex_eventlogs.release()
                    state=1  
                else:
                    print("Container is not running (abort update)") if log_file else None 
            else:      
                print("Schedule Resume Request: ", threading.current_thread().getName(), ' - Container: instance', container_number) if log_file else None 
                mutex_execInfo.acquire()
                for container_info in execInfo_list:
                    if (container_info.get_container_number() == request_.get_request_id()):      
                        parallelism_container= scheduler_container.schedule_parallelism(resources_availables, container_info.get_inter_exec_parallelism(), container_info.get_intra_exec_parallelism())   
                        if parallelism_container:
                            parallelism_apply= parallelism_container[0]+parallelism_container[1]
                            # Asignar paralelismo al contenedor
                            container_info.set_inter_exec_parallelism(parallelism_container[0])
                            container_info.set_intra_exec_parallelism(parallelism_container[1])
                            # Reanudar ejecucion del contenedor
                            print("Execute resume container...") if log_file else None 
                            container_info.resume_container() 
                            # Despertar al hilo cliente para que escuche mensajes
                            container_info.signal_execution()
                            # Almacenar evento
                            mutex_eventlogs.acquire()
                            event_logs.save_event(events.RESUME_CONTAINER, container_id=container_number)
                            event_logs.finish_container_event(container_number, [])
                            event_logs.init_container_event(container_number,parallelism_container[0]+parallelism_container[1], instance_number)
                            mutex_eventlogs.release()
                            state=1 
                mutex_execInfo.release() 
    if (parallelism_apply !=0) and (parallelism_apply < resources_availables):
        print("Free excedded resources: ", ) if log_file else None 
        system_info.free_resources(resources_availables-parallelism_apply)               
    return state

def updateExecutionInstance(container_name, new_inter_parallelism, new_intra_parallelism, resources_availables):
    log_file=False
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
                print('Old Parallelism: Inter=', old_interParallelism, ' - Intra=', old_intraParallelism, ' New Parallelism: Inter=', new_inter_parallelism, ' - Intra=', new_intra_parallelism) if log_file else None 
                # Si es menor a cero quiere decir que vamos a decrementar el paralelismo total del contenedor
                if resources_availables<0:
                    ok = x.update_parallelism(new_inter_parallelism, new_intra_parallelism)
                    parallelism_apply= (new_inter_parallelism+new_intra_parallelism) - (old_interParallelism+old_intraParallelism)
                    print("Free resources in container reassigment") if log_file else None 
                    ok=True
                else:
                    parallelism_list= scheduler_container.schedule_parallelism(resources_availables, new_inter_parallelism-old_interParallelism, new_intra_parallelism-old_intraParallelism)
                    if parallelism_list:
                        print("Parallelism Apply: ", parallelism_list[0] + parallelism_list[1]) if log_file else None 
                        if (parallelism_list[0] != 0) and (parallelism_list[1] != 0):      
                            ok = x.update_parallelism(old_interParallelism+parallelism_list[0] , old_intraParallelism+parallelism_list[1])
                            print("Update both parallelism") if log_file else None 
                        else:
                            if (parallelism_list[0] != 0):
                                 ok = x.update_parallelism(old_interParallelism+parallelism_list[0] , 0)
                                 print("Update inter parallelism") if log_file else None 
                            else:
                                 ok = x.update_parallelism(0 , old_intraParallelism+parallelism_list[1])
                                 print("Update intra parallelism") if log_file else None 
                        parallelism_apply= parallelism_list[0] + parallelism_list[1]                    
                        ok=True
                    else:
                        ok=False
    mutex_execInfo.release()  
    return ok, parallelism_apply

# System Info Safe
def oldest_reassigment(resources_availables, increase_or_reduce, increment_active_containers=False, amount_reduce=0):
    log_file=False
    try:
        priority=-1
        for c in execInfo_list:
            if(priority <  c.get_priority()):
                priority = c.get_priority()
        print("Reassigment Containers with oldest policy") if log_file else None 
        if increase_or_reduce:
            mutex_execInfo.acquire()
            for container in execInfo_list:
                if(isinstance(scheduler_container,Priority)):
                    if (c.get_priority() != priority):
                        # Jump this container because have minor priority
                        continue
                if container.get_state() == 'start':
                    ok=False
                    if increment_active_containers:
                        interparallelism_required= 0
                        intraparallelism_required= resources_availables
                        intraUser_parallelism= container.get_intra_user_parallelism() + intraparallelism_required
                    else:
                        interUser_parallelism= container.get_inter_user_parallelism()
                        intraUser_parallelism= container.get_intra_user_parallelism()
                        interExec_parallelism= container.get_inter_exec_parallelism()
                        intraExec_parallelism= container.get_intra_exec_parallelism()
                        interparallelism_required= interUser_parallelism -  interExec_parallelism
                        intraparallelism_required= intraUser_parallelism -  intraExec_parallelism
                    if resources_availables >0:
                        # Aumentar todo el paralelismo al contenedor
                        if (interparallelism_required>0 and intraparallelism_required>0):
                            if resources_availables >= (interparallelism_required + intraparallelism_required):             
                                container.update_parallelism(interUser_parallelism, intraUser_parallelism)
                                print("Update total parallelism in container: ", container.get_container_name()) if log_file else None 
                                resources_availables-=interparallelism_required-intraparallelism_required                       
                            else:
                                # Aumentar solo el intra paralelismo
                                if (resources_availables >= intraparallelism_required):
                                    container.update_parallelism(intra_parallelism=intraExec_parallelism+intraparallelism_required)
                                    resources_availables= resources_availables - intraparallelism_required
                                    print("Update total intra parallelism in container: ", container.get_container_name(), " to: ", intraExec_parallelism+intraparallelism_required) if log_file else None 
                                else:
                                    container.update_parallelism(intra_parallelism=intraExec_parallelism+resources_availables) 
                                    print("Update intra parallelism in container: ", container.get_container_name(), "to: ", intraExec_parallelism+resources_availables) if log_file else None 
                                    resources_availables=0
                                # Intentar aumentar el inter paralelismo con los recursos disponibles restantes (si es que hay)
                                # if (resources_availables>0):
                                #     container.update_parallelism(inter_parallelism=interExec_parallelism+resources_availables)
                                #     resources_availables=0 
                                #     print("Update inter parallelism in container: ", container.get_container_name(), "to: ", interExec_parallelism+resources_availables)
                            ok=True
                        else:
                            if(intraparallelism_required>0):
                                if (resources_availables >= intraparallelism_required):
                                    container.update_parallelism(intra_parallelism=intraUser_parallelism)
                                    resources_availables= resources_availables - intraparallelism_required
                                    print("Update total intra parallelism in container: ", container.get_container_name(), " to: ", intraUser_parallelism) if log_file else None 
                                else:
                                    container.update_parallelism(intra_parallelism=intraExec_parallelism+resources_availables) 
                                    print("Update intra parallelism in container: ", container.get_container_name(), "to: ", intraExec_parallelism+resources_availables) if log_file else None 
                                    resources_availables=0
                                ok=True
                            else:
                                if(interparallelism_required>0):
                                    if (resources_availables >= interparallelism_required):
                                        container.update_parallelism(inter_parallelism=interUser_parallelism)
                                        resources_availables= resources_availables - interparallelism_required
                                        print("Update total inter parallelism in container: ", container.get_container_name(), " to: ", interUser_parallelism) if log_file else None 
                                    else:
                                        container.update_parallelism(inter_parallelism=interExec_parallelism+resources_availables) 
                                        print("Update inter parallelism in container: ", container.get_container_name(), "to: ", interExec_parallelism+resources_availables) if log_file else None 
                                        resources_availables=0
                                    ok=True
                    if ok:
                        mutex_eventlogs.acquire()
                        event_logs.save_event(events.REASSIGMENT_RESOURCES, container_id=container.get_container_number(), inter_exec=container.get_inter_exec_parallelism(), intra_exec=container.get_intra_exec_parallelism())
                        event_logs.finish_container_event(container.get_container_number(),  [])
                        event_logs.init_container_event(container.get_container_number(), container.get_inter_exec_parallelism()+container.get_intra_exec_parallelism(), container.get_container_number())
                        mutex_eventlogs.release()
                    if resources_availables == 0:
                        break
            mutex_execInfo.release()
        else:
            # reducir el paralelismo de los contenedores mas viejo liberando la cantidad de recursos solicitados (amount_reduce)
            pass     
        return resources_availables

    except BaseException as e:
        print(repr(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print("Base error")
        sys.exit(1)

# Fin Métodos Generales #

# Métodos asignados a hilos #

# Save system status (cpu and memory use) in file
def SystemControl(thread_id):
    log_file= False
    print('System Control Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)   
    try:
        gap=30
        occupation_register= [] 
        memory_register= []
        coresUsed_register= []
        mutex_finishExecution.acquire()
        while not finish_execution:
            #occ_res= system_info.system_occupation()
            occ_res= psutil.cpu_percent(1)
            print('Occupation resources: ' , occ_res) if log_file else None
            occupation_register.append(occ_res)
            memory_register.append(psutil.virtual_memory()[2])
            mutex_systemInfo.acquire()
            coresUsed_register.append(system_info.system_occupation())
            mutex_systemInfo.release()
            mutex_finishExecution.release()
            time.sleep(gap)
            mutex_finishExecution.acquire()
        mutex_finishExecution.release()
        with open('Data/log/occupation_timeline.csv', "w") as file:
            gap_count=0
            i=0
            for data in occupation_register:
                file.write(str(gap_count))
                file.write(',')
                file.write(str(data))
                file.write(',')
                file.write(str(memory_register[i]))
                file.write(',')
                file.write(str(coresUsed_register[i]))
                file.write('\n')
                gap_count= gap_count + gap
                i+=1
    except BaseException as e:
        print(repr(e)) if log_file else None
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno) if log_file else None
        print("Base error")  if log_file else None
    except:
        print("Unexpected error :(") if log_file else None

def generatePauseResumeRequest(thread_id):
    log_file=False
    print('PauseResumeRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident) if log_file else None    
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
            print("Container not exist in List") if log_file else None
            skip=True
        mutex_containerList.release()     
        if not skip:       
            request_ = Pause(container_name)
            scheduler_container.add_new_request(request_, request_.get_priority())
            print("Schedule Pause request to container: ", container_name) if log_file else None
            # Avisar al hilo de atencion que se encoló una nueva petición.
            with cv_attention:
                cv_attention.notify()
                #print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)
                
            time_wait= int(normal_time[0])  
            time.sleep(time_wait)
            request_ = Resume(container_name)
            scheduler_container.add_new_request(request_, request_.get_priority())   
            print("Schedule Resume request to container: ", container_name)  if log_file else None
            # Avisar al hilo de atencion que se encoló una nueva petición.
            with cv_attention:
                cv_attention.notify()
                #print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)              
        mutex_finishExecution.acquire()
    mutex_finishExecution.release()
    print("Finish Pause-Resume request thread") if log_file else None

# Crear contenedores indicando la imagen de docker utilizada y los valores y distribuciones de la cantidad de contenedores, tiempo y recursos por contenedor.
def creation_requests(docker_container, number_containers=1, time_distribution="static", time_gap=[1,0], resources_distribution="static", resources_per_container=[1,2], filename= ''):
    log_file=False
    try:
        request_file = open(filename, 'w')
        global creation_requests_terminate
        instance_container=0
        while number_containers !=0:
            if time_distribution == "normal":
                mean= time_gap[0]
                desviation= time_gap[1]
                time_sleep = np.random.normal(mean, desviation, 1)[0]
            else:
                time_sleep= time_gap[0]
            if resources_distribution == "random":
                min= resources_per_container[0]
                max= resources_per_container[1]
                resources_container = np.random.randint(max-min, size=1)[0]
                resources_container+= min
            else:
                resources_container= resources_per_container[0]
            priority= np.random.randint(5, size=1)[0]
            line ='execution,' + str(instance_container) + ',' + docker_container + ',' + str(resources_container) + ',' + str(time_sleep) + ',' + str(priority) + '\n'
            request_file.write(line)
            time.sleep(int(time_sleep))
            print("Create request...") if log_file else None
            scheduling_requests.acquire()
            if(isinstance(scheduler_container, Priority)):
                request_exec = Start(str(instance_container), docker_container,1,resources_container-1, priority)
                scheduler_container.add_new_request(request_exec, priority)
            else:
                request_exec = Start(str(instance_container), docker_container,1,resources_container-1, 0)
                scheduler_container.add_new_request(request_exec, 0)
            scheduling_requests.release()   
            mutex_eventlogs.acquire()
            event_logs.save_event(events.GENERATE_REQUEST_EXE, instance_container, inter_user=request_exec.get_inter_parallelism(), intra_user=request_exec.get_intra_parallelism())
            event_logs.init_container_event(-1, resources_container, instance_container)
            time.sleep(1)
            event_logs.finish_container_event(-1, [])
            mutex_eventlogs.release()
            instance_container= instance_container+1
            number_containers= number_containers-1
            # Despertar al hilo consumidor
            with cv_attention:
                cv_attention.notify()   
    except BaseException as e:
        print(repr(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno) 
        print("Base error")
    except:
        print("Unexpected error :(") 
    
    request_file.close()
    creation_requests_terminate=True
    
    print("Finish creation requests")


# Leer la planificacion de los contenedores desde un fichero donde cada fila indica [tipo de peticion, instancia, imagen de docker, inter paralelismo, intra paralelismo]  
def read_requests(thread_id, number_containers, filename):
    log_file=False
    number_line=0
    try:
        global creation_requests_terminate
        print('Read requests...') if log_file else None
        with open(filename) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                priority= int(row[5])
                time_csv= row[4].replace('[', '')
                time_csv= time_csv.replace(']', '')
                time.sleep(float(time_csv))
                if (row[0]=='execution'):
                    request_exec = Start(row[1], row[2],1,int(row[3])-1, priority)
                    scheduling_requests.acquire()
                    if(isinstance(scheduler_container, Priority)):
                        scheduler_container.add_new_request(request_exec, priority)
                    else:
                        scheduler_container.add_new_request(request_exec, 0)
                    scheduling_requests.release()   
                    mutex_eventlogs.acquire()
                    event_logs.save_event(events.GENERATE_REQUEST_EXE, int(row[1]), inter_user=1, intra_user=int(row[3])-1)
                    event_logs.init_container_event(-1, int(row[3]), row[1])
                    event_logs.finish_container_event(-1, [])
                    mutex_eventlogs.release()   
                    print('Schedule execution request')
                    number_line+=1
                else:
                    request_up= Update(row[1], 1, int(row[3])-1, priority)
                    scheduling_requests.acquire()
                    if(isinstance(scheduler_container, Priority)):
                        scheduler_container.add_new_request(request_up, int(row[5]))
                    else:
                        scheduler_container.add_new_request(request_up, 0)
                    scheduling_requests.release()
                    mutex_eventlogs.acquire()
                    event_logs.save_event(events.GENERATE_REQUEST_UP, row[1])
                    event_logs.init_container_event(-2, int(row[3]), row[1])
                    time.sleep(1)
                    event_logs.finish_container_event(-2, [])
                    mutex_eventlogs.release()  
                    print('Schedule update request')
                    pass
                with cv_attention:
                    cv_attention.notify()
        creation_requests_terminate=True
        print("Finish read request thread")
    except BaseException as e:
        print(repr(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print("Base error")

def remove_container(container_name, resources_free_self=False):
    log_file= False
    container_eliminated=False
    # Buscar contenedor en la lista
    # Eliminar objeto contenedor de la lista de contenedores activos
    mutex_execInfo.acquire()
    for elem in execInfo_list:
        if (elem.get_container_name() == container_name):         
            # Encolar paralelismo liberado por el contenedor
            resources_free= elem.get_inter_exec_parallelism() + elem.get_intra_exec_parallelism()
            # Consulta si elimina el mismo contenedor los recursos usados o los elimina el hilo de atencion (False los elimina el hilo de atencion)
            if resources_free_self== False:
                q_finish_container.put([resources_free, container_name])
            print("Push Free Parallelism of Container: ", container_name, " Parallelism: ", elem.get_inter_exec_parallelism() + elem.get_intra_exec_parallelism()) if log_file else None
            #Despertar al hilo de atencion
            with cv_attention:
                cv_attention.notify()
                #print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)       
            execInfo_list.remove(elem)
            #print('Eliminate Container ', container_name, ' because it finished')
            container_eliminated= True
            break
    mutex_execInfo.release()
    # Eliminar el nombre de la lista de contenedores activos para que no se generen nuevas peticiones de actualización
    mutex_containerList.acquire()
    #print("Remove container from container list")
    containerName_list.remove(container_name)
    mutex_containerList.release()
    return container_eliminated, resources_free

def container_failed_attention(instance_number, container_name, request_):
    log_file=True
    global containers_failed
    print("Stop container: ", container_name) if log_file else None
    docker_command= 'docker container stop instance' + str(instance_number) + ' && docker container prune -f'
    print(docker_command) if log_file else None
    process_command = Popen(docker_command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    stdout, stderr = process_command.communicate()
    if stdout:
        print(stdout) if log_file else None
    else:
        print(stderr) if log_file else None
    # Wait docker prune...
    time.sleep(30)

    # Buscar recursos ocupados por el contenedor
    for elem in execInfo_list:
        if (elem.get_container_name() == container_name):         
            # Encolar paralelismo liberado por el contenedor
            resources_free= elem.get_inter_exec_parallelism() + elem.get_intra_exec_parallelism()
            inter_paralelism= elem.get_inter_exec_parallelism()
            intra_parallelism= elem.get_intra_exec_parallelism()
            image= elem.get_image()
            elem.set_state('failed')
    # Liberar recursos ocupados 
    mutex_systemInfo.acquire()
    system_info.free_resources(resources_free)
    mutex_systemInfo.release()
    print("Generate new request for ", container_name) if log_file else None
    request_restart = Restart(str(instance_number), container_name, inter_paralelism, intra_parallelism, image, request_.get_priority())
    scheduling_requests.acquire()
    scheduler_container.add_new_request(request_restart, request_.get_priority())
    scheduling_requests.release() 
    mutex_eventlogs.acquire() 
    event_logs.init_container_event(-3, instance_number, instance_number)
    time.sleep(1)
    event_logs.finish_container_event(-3, [])
    mutex_eventlogs.release()
    mutex_containersFailed.acquire()
    containers_failed= containers_failed+1
    mutex_containersFailed.release()
    # Despertar al hilo consumidor
    with cv_attention:
        cv_attention.notify()    

def container_client(clientsocket,addr,container_name, instance_number, interExec_parallelism, intraExec_parallelism, thread_id, request_, restart=False):
    global tf_version
    log_file=False
    container_eliminated= False
    msg=''
    ok=False

    data= {
        "container": int(instance_number),
        "tf_use": tf_version,
        "inter_parallelism": int(interExec_parallelism),
        "intra_parallelism": int(intraExec_parallelism)
    }
    json_data_socket._send(clientsocket, data)
    
    #Recibir mensaje de inicio
    attemps=0
    while not ok:
        try:
            msg= json_data_socket._recv(clientsocket)
            #print('Message recieved from Client ID: '+ str(instance_number)+" - Message: "+ msg["status"]) 
            mutex_eventlogs.acquire()
            event_logs.save_event(events.ATTENTION_REQUEST_EXE, request_id=request_.get_request_id(), container_id=instance_number, inter_exec=interExec_parallelism, intra_exec=intraExec_parallelism)
            event_logs.init_container_event(instance_number, interExec_parallelism+intraExec_parallelism, instance_number) 
            mutex_eventlogs.release()
            ok=True
        except socket.timeout: # fail after 60 second of no activity
            #print("Didn't receive init! [Timeout] - Container: " + str(instance_number))
            attemps=attemps+1
            if attemps==10:
                # Reiniciar contenedor porque no responde al inicio
                container_failed_attention(instance_number, container_name, request_)
                attemps=0

    loop=0
    # Esperar mensaje de finalización. 
    while not container_eliminated:
        try:
            print('Wait message: ', container_name) if log_file else None
            # Recibir mensaje de finalización o problema del contenedor
            msg= json_data_socket._recv(clientsocket)

            print('Container: ', container_name, ' - Recieve msg: ', msg["status"]) if log_file else None
            # if loop==0:
            #     print('Message recieved from Client ID: '+ str(instance_number)+" - Message: "+ msg["status"])
            # loop=loop+1
            # print (container_name, "send message: ", msg) (ver por qué recibe tantos mensajes vacios)
            if (('exit' in msg["status"]) or (msg["status"] == 'exit')):
                filename_epochs= "models/output_" + str(instance_number) + "_" + tf_version + ".txt"
                time_epochs= TimeEpochs().process_TF_file(filename_epochs)
                mutex_eventlogs.acquire()
                event_logs.save_event(events.FINISH_CONTAINER, container_id=instance_number)
                print("Epochs in container:", container_name) if log_file else None
                print("Time epochs:", time_epochs)
                event_logs.finish_container_event(instance_number, time_epochs)
                mutex_eventlogs.release()

                print("Remove Container: ", container_name) if log_file else None

                # Eliminar contenedor del planificador 
                container_eliminated, resources_free= remove_container(container_name)

                # Informar en caso de que no se pueda eliminar el contenedor
                if not container_eliminated:
                    print('The container ', container_name, ' could not be deleted') if log_file else None
                else: 
                    # Enviar ACK indicando finalizacion de la eliminacion del cliente
                    print("Send ACK to client: " + container_name) if log_file else None
                    data={
                        "container": int(instance_number),
                        "inter_parallelism": -1,
                        "intra_parallelism": -1
                    }
                    json_data_socket._send(clientsocket, data)
        except socket.timeout: # fail after 60 second of no activity
            print("Didn't receive data! [Timeout] - Container: " + container_name) if log_file else None
            print("Send live message..." + container_name) if log_file else None
            data={
                "container": instance_number,
                "inter_parallelism": -2,
                "intra_parallelism": -2
            }
            json_data_socket._send(clientsocket, data)
            print("Wait live response of container: ", container_name) if log_file else None
            try:
                msg= json_data_socket._recv(clientsocket)
                print("Message Recieved: ", msg["status"] , " - ", container_name) if log_file else None
                if msg["status"] == 'live':
                    print("Container is live: ",  container_name) if log_file else None
                else:  
                    # Hacer el else una función ya que se repite el código tambien en el except del try actual
                    print("Execution container is dead: ", container_name)
                    mutex_eventlogs.acquire()
                    event_logs.finish_container_event(instance_number, [])
                    event_logs.save_event(events.FINISH_CONTAINER, container_id=instance_number)
                    mutex_eventlogs.release()
                    container_failed_attention(instance_number, container_name, request_)
                    container_eliminated= True
                    filename_epochs= "models/output_" + str(instance_number) + "_" + tf_version + ".txt"
                    if os.path.exists(filename_epochs):
                        os.remove(filename_epochs)
                    else:
                        print("The file does not exist") if log_file else None
            except socket.timeout: # fail after 60 second of no activity
                print("Not message recieved: ", container_name) if log_file else None
                mutex_eventlogs.acquire()
                event_logs.finish_container_event(instance_number, [])
                event_logs.save_event(events.FINISH_CONTAINER, container_id=instance_number)
                mutex_eventlogs.release()
                container_failed_attention(instance_number, container_name, request_)
                container_eliminated= True
                filename_epochs= "models/output_" + str(instance_number) + "_" + tf_version + ".txt"
                if os.path.exists(filename_epochs):
                    os.remove(filename_epochs)
                else:
                    print("The file does not exist") if log_file else None
        except socket.error as ex: 
            print("Connection reset by peer with request count=" + str(loop))
            print(ex)
        except BaseException as e:
            print(repr(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print("Base error")
        finally:
            if not container_eliminated:
                print("Check if container has paused: ", container_name) if log_file else None
                paused=False
                mutex_execInfo.acquire()
                for elem in execInfo_list:
                    if (elem.container_name == container_name):
                        if(elem.get_state() == "pause"):
                            print("Paused container: ", container_name) if log_file else None
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
    with cv_attention:
        cv_attention.notify()
    print("Finish Client Thread - Container: ", container_name)

def attentionRequest(socket_schedule, thread_id):
    log_file=True
    try:
        print('AttentionRequest Thread:', threading.current_thread().getName()) if log_file else None
        request_pending=False
        port_host=8787
        global finish_execution
        global reassigment
        global priority_reassigment
        global not_control
        global global_resources_ok
        #mutex_finishExecution.acquire()
        while not is_finish_attention(): # esto tenerlo en cuenta para vaciar colas de peticiones pero no como condicion de corte
            #mutex_finishExecution.release()
            with cv_attention:
                # Esperar a que alguno de los demas hilos avise que hay peticiones pendientes (ejecución, actualización o eliminación de contenedores)
                cv_attention.wait()
                #print('Wake up:', threading.current_thread().getName())
            if not q_finish_container.empty():
                
                print('Attention finish request: ',threading.current_thread().getName()) if log_file else None
                # Atender peticiones de finalización de contenedores
                while not q_finish_container.empty():
                    data = q_finish_container.get()
                    mutex_systemInfo.acquire()
                    print("Free resources of container: ", data[0]) if log_file else None
                    system_info.free_resources(int(data[0]))
                    mutex_systemInfo.release()
                    print("Join Client Thread: ", data[1]) if log_file else None
                    mutex_dict_client_threads.acquire()
                    dict_client_threads[data[1]].join()
                    mutex_dict_client_threads.release()
                    print("Finish client thread:", data[1]) if log_file else None

                # reasigno contenedores con prioridad de los contenedores mas viejos (indicando que se aumenten sus recursos asignados)
                mutex_systemInfo.acquire()
                resources_availables= system_info.check_resources()
                if resources_availables>0 and reassigment and priority_reassigment: 
                    system_info.apply_resources(resources_availables, not_control)
                    mutex_systemInfo.release()
                    resources_availables= oldest_reassigment(resources_availables, True)
                    if resources_availables > 0:
                        mutex_systemInfo.acquire()
                        system_info.free_resources(resources_availables)
                        mutex_systemInfo.release()
                else:
                    mutex_systemInfo.release()

            if (scheduler_container.get_reassigment_type() == "max_prop"):
                #Esperar a obtener el acceso exclusivo (para evitar que se encolen nuevas peticiones)
                scheduling_requests.acquire()
                mutex_systemInfo.acquire()
                resources_availables= system_info.check_resources()
                #print("Requested resources in factor prop: ", resources_availables)
                if (resources_availables>0):
                    mutex_execInfo.acquire()
                    scheduler_container.calculate_factor_prop(resources_availables, execInfo_list)
                    mutex_execInfo.release()
            else:
                mutex_systemInfo.acquire()
                resources_availables= system_info.check_resources()
            # Intentar atender las peticiones pendientes de ejecucion/actualizacion
            print('Attention act/exe request pending: ',threading.current_thread().getName()) if log_file else None
            q_aux= queue.Queue()
            if resources_availables >0:
                request_= scheduler_container.get_pending_request()
                if not request_:
                    print("Not request in pending queue") if log_file else None
                while (request_):
                    requested_resources = schedule_resources(request_, resources_availables)
                    state=0
                    if (requested_resources!=0):
                        # Intentar planificar peticion pendiente    
                        mutex_systemInfo.release()   
                        state= schedule_request(request_, socket_schedule, port_host, requested_resources, thread_id)
                        mutex_systemInfo.acquire()  
                    # Verificar estado de la planificacion de peticion        
                    if state==0:
                        print ("Pending petition could not be answered") if log_file else None
                        q_aux.put(request_)
                        system_info.free_resources(requested_resources)
                    else:
                        if isinstance(request_, Start) or isinstance(request_, Restart):
                            port_host= port_host+1 
                    resources_availables= system_info.check_resources()
                    print("Resources availables after schedule: " + str(resources_availables)) if log_file else None
                    request_ = scheduler_container.get_pending_request()
                mutex_systemInfo.release()
                # Almacenar las peticiones antiguas pendientes en la cola nuevamente
                while (not q_aux.empty()):
                    request_= q_aux.get()
                    scheduler_container.add_pending_request(request_, request_.get_priority())
            else:
                mutex_systemInfo.release()
            print('Attention new act/exe request: ',threading.current_thread().getName()) if log_file else None
            # Intentar atender nuevas peticiones de ejecucion/actualizacion
            mutex_systemInfo.acquire()
            resources_availables= system_info.check_resources()
            
            if resources_availables > 0:
                request_= scheduler_container.get_new_request()
                while ((request_)):
                    requested_resources = schedule_resources(request_, resources_availables)            
                    mutex_systemInfo.release()
                    print("Requested_resources: ", requested_resources) if log_file else None
                    if ((not isinstance(request_, Pause)) or (not_control)):
                        state=0
                        if(requested_resources !=0):
                            state= schedule_request(request_, socket_schedule, port_host, requested_resources, thread_id)  
                        # Verificar si no se pudo atender la peticion
                        if (state==0):
                            if isinstance(request_, Resume):
                                print("Resume request pending") if log_file else None
                                scheduler_container.add_pending_request(request_, request_.get_priority())
                            else:
                                # Verificar si la cantidad de paralelismo solicitada excede el máximo de la máquina
                                if((request_.get_inter_parallelism()+request_.get_intra_parallelism())>system_info.total_cores()):
                                    print("Request discarded because the parallelism requested exceeds the maximum number of cores of the machine") if log_file else None
                                else:
                                    print("New request pending") if log_file else None
                                    scheduler_container.add_pending_request(request_, request_.get_priority())
                            system_info.free_resources(requested_resources)
                        else: 
                            if isinstance(request_, Start) or isinstance(request_, Restart):
                                port_host= port_host+1   
                    else:
                        if not isinstance(request_, Pause):
                            print("Discard this request") if log_file else None
                    mutex_systemInfo.acquire()
                    resources_availables= system_info.check_resources()
                    print("Resources availables after schedule: " + str(resources_availables)) if log_file else None
                    request_= scheduler_container.get_new_request()  
            # Reassigment resources if its enable and have free resources and enable for reassigment
            if resources_availables>0 and reassigment: 
                # print("Wait for reassigment...") if log_file else None
                # time.sleep(30)
                print("Reasigment Resources...") if log_file else None 
                system_info.apply_resources(resources_availables, not_control)
                mutex_systemInfo.release()
                resources_availables= oldest_reassigment(resources_availables, True)
                if resources_availables > 0:
                    mutex_systemInfo.acquire()
                    system_info.free_resources(resources_availables)
                    mutex_systemInfo.release()
            else:
                mutex_systemInfo.release()
            mutex_systemInfo.acquire()
            if(system_info.system_occupation() > 100) and (not not_control):
                global_resources_ok= False
                raise Exception("Resources used is more than system resources :(")
            mutex_systemInfo.release()
            if(scheduler_container.get_reassigment_type()=="max_prop"):
                scheduling_requests.release()

        print (" Attention pending resumes...") if log_file else None
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
                        print("Espero finalizacion de un contenedor...") if log_file else None
                        cv_attention.wait()  
                    mutex_systemInfo.acquire()   
                    while not q_finish_container.empty():
                        data= q_finish_container.get()
                        print("Free resources count: ", data[0]) if log_file else None
                        system_info.free_resources(data[0])
                        print("Join Client Thread: ", data[1]) if log_file else None
                        mutex_dict_client_threads.acquire()
                        dict_client_threads[data[1]].join()
                        mutex_dict_client_threads.release()
                    resources_availables= system_info.check_resources()
                    requested_resources = schedule_resources(request_, resources_availables) 
                    mutex_systemInfo.release() 
                    if requested_resources >0:
                        state= schedule_request(request_, socket_schedule, port_host, requested_resources, thread_id)     
                        if state != 0:
                            complete=True
                        else: 
                            mutex_systemInfo.acquire()  
                            system_info.free_resources(resources_availables)
                            mutex_systemInfo.release()
                mutex_execInfo.acquire()           
        mutex_execInfo.release()
        if (resources_availables == system_info.total_cores()):
            print("Correct total resources availables before finish")
    except BaseException as e:
        print(repr(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print("Base error")
    except (SyntaxError, IndentationError, NameError) as err:
        print(err)
    except socket_schedule.error as err:
        print(err)
        print("Error in socket")
    except:
        print("Unexpected error :(")
    
    print("Finish attention thread")

# Programa Principal #
if __name__ == "__main__":
    
    try:

        #print("Scheduler for Instances TF")

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
        
        if len(sys.argv) != 1:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 0")
            raise NameError('Invalid amount of arguments')
        
        with open('Scheduler-host/parameters.json') as f:
            variables = json.load(f)

        s_policy = variables["policy"]
        assigment_policy= variables["assignment_policy"]
        tf_version= variables["tf_version"]
        tf_model= variables["tf_model"]
        tf_dockerimage= variables["tf_dockerimage"]
        number_containers= variables["number_containers"]
        time_distribution= variables["time_distribution"]
        time_gap= variables["time_gap"]
        resources_distribution= variables["resources_distribution"]
        resources_per_container= variables["resources_per_container"]
        get_requests= variables["get_requests"]
        filename_requests= variables["requests_file"]
        if(s_policy == "fcfs"):
            scheduler_container= FCFS(assigment_policy)
        else:
            scheduler_container= Priority(assigment_policy, 5)
        event_logs= TraceLog(scheduler_container.get_reassigment_type())
        event_logs.set_tf_model(tf_model)
        event_logs.set_tf_version(tf_version)


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
        if get_requests == "file":
            request_thread = threading.Thread(target=read_requests, args=(number_thread, number_containers, filename_requests,))
        else:
            request_thread = threading.Thread(target=creation_requests, args=(tf_dockerimage, number_containers, time_distribution, time_gap, resources_distribution, resources_per_container,filename_requests,))
        event_logs.add_thread()
        number_thread=number_thread+1

        # Crear hilo para el control de los recursos
        control_thread = threading.Thread(target=SystemControl, args=(number_thread,))
        event_logs.add_thread()
        number_thread= number_thread+1
        
        # Iniciar todos los hilos
        attention_thread.start()
        request_thread.start()
        control_thread.start()
        
        # Esperar la terminación de los hilos
        attention_thread.join()
        if(global_resources_ok):
            request_thread.join()
            control_thread.join()

            '''
            # Esperar la terminacion de los hilos clientes
            print("Join client threads...")
            while not q_client_threads.empty():
                client= q_client_threads.get()
                client.join()
            '''
            socket_schedule.close()

            # Almacenar en un archivo la cantidad de contenedores que fallaron
            with open('./Data/log/containers_failed.txt', mode='w') as f:
                f.write(str(containers_failed))
            print("Save data log...")
            event_logs.save_CSV('./Data/log/', 'scheduler_events.txt')
            print("Save Gantt events...")
            event_logs.save_gantt('./Data/log/', 'gantt_events.txt')
            print("Calculate Metrics...")
            # event_logs.calculate_throughput('./Data/log/')
            event_logs.calculate_meantime_container(number_containers, './Data/log/', 'gantt_events.txt')
            #print("Plot Gantt diagram...")
            #event_logs.plot_gantt()
            print("Finish Scheduler :)")
        else:
            print("resources used is more than global resources in system :(")
            sys.exit(1)
    
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
# Fin de Programa Principal #