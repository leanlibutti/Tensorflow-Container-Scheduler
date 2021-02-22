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
from scheduling_policy import FFSnotReassignment, FFSReassignment
import copy
from Commons.trace import TraceLog
from Commons import events

#Mutex para acceder al trace log
mutex_eventlogs= threading.Lock()

# Almacena la informacion de los eventos en el planificador
event_logs= TraceLog(1)

#Mutex para acceder al proximo numero de hilo
mutex_numberThread= threading.Lock()

# Numero de hilo que identifica unicamente a cada uno
number_thread=1

# Encargada de manejar los recursos disponibles y utilizados en el sistema
system_info = systemInfo()

# Mutex para acceder con exclusión mutua a la información del sistema
mutex_systemInfo = threading.Lock()

# Política de asignación de recursos a los contenedores (puede modificarse)
scheduler_container= FFSnotReassignment()

#Indica si las peticiones de ejecucion se manejan con prioridad o no
priority_queue = False

# Cola sin prioridad para almacenar peticiones de ejecucion y actualizacion 
q_normal_exec_update = queue.Queue(10)

# Cola con prioridad que puede almacenar hasta 10 peticiones de ambos tipos (ejecución y actualización)
# Si se desea colocar cuando está llena se realiza un bloqueo hasta que haya lugar
q_priority_exec_update = queue.PriorityQueue(10)

# Cola para almacenar peticiones de finalización de contenedor (almacena el paralelismo total liberado)
q_finish_container= queue.Queue(10)

# Cola para almacenar peticiones pendientes de atencion
q_request_pending= queue.Queue()

client_threads= queue.Queue()

# Variable que indica si el hilo Atencion debe replanificar los hilos de los contenedores
rescheduling_containers= False

# Variable condición utilizada para avisar al hilo Atencion de que hay pedidos pendientes en alguna cola.
cv_attention = threading.Condition()

# Crear estructura de petición (namedtuple) con los siguientes datos:
# - Tipo de peticion (nueva ejecucion o actualizar paralelismo)
# - Comando de sistema a ejecutar
# - Paralelismo Inter
# - Paralelismo Intra
Request = namedtuple('Request', ['request_type', 'container_name', 'docker_image', 'inter_parallelism', 'intra_parallelism'])

# Mutex para la lista de instancias TF en ejecución
mutex_execInfo= threading.Lock()

# Lista que almacena la información de cada instancia de TF que se encuentra en ejecución (puede tener instancias que ya terminaron)
execInfo_list=[]

# Mutex para lista de nombres de contenedores en ejecución
mutex_containerList= threading.Lock()

# Lista de nombres de contenedores en ejecución (para que el hilo update sepa a cuáles contenedores puede actualizar)
containerName_list=[]

# Utilizada para bloquear al hilo generador de peticiones de actualizaciones hasta que haya ejecuciones disponibles.
cv_update = threading.Condition()

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

# Fin de metodos para manejo de señales

# Métodos Generales #

def schedule_request(request, socket_schedule, instance_number=0, port_host=0, resources_availables=0, thread_id=0):

    global number_thread

    if request.request_type == 'execution':

        # Atender peticion de actualizacion

        print('Schedule Execution Request: ',threading.current_thread().getName())

        parallelism_container= scheduler_container.schedule_parallelism(resources_availables, request.inter_parallelism, request.intra_parallelism)

        # Accede a consultar si hay paralelismo disponible (system_info es thread-safe en este momento)
        if parallelism_container:
        
            container_name= 'instance' + str(instance_number)
            
            # Comando para iniciar contenedor con una imagen dada en la petición (opciones dit permiten dejar ejecutando el contenedor en background)
            print("Creating Docker Container...")

            docker_command= 'docker run -dit --name '+ container_name + ' -p ' + str(port_host) + ':8787 --volume $HOME/Documentos/gitlab/tensorflow/scheduler:/home/Scheduler ' + request.docker_image
            
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
                    client_threads.put(tmp_thread)
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
                exec_info = ExecutionInfo(container_name, instance_number, port_host, process_id, request.inter_parallelism, request.intra_parallelism, parallelism_container[0], parallelism_container[1], c)

                # Almacenar instancia de execución en la lista de ejecuciones activas (es thread safe)
                mutex_execInfo.acquire()
                execInfo_list.append(exec_info)
                mutex_execInfo.release()

                # Almacenar nombre del contenedor para que en el update pueda actualizarlos 
                mutex_containerList.acquire()
                containerName_list.append(container_name)
                mutex_containerList.release()

                # Despertar al hilo GenerateUpdateRequest cuando ya hay instancias en ejecución 
                if execInfo_list.count == 1:
                    with cv_update:
                        cv_update.notify()

                state=1
        else:
            state=0

    else:
        # Atender petición de actualización

        print('Schedule Update Request: ',threading.current_thread().getName() + ' - Container: ' + str(instance_number))

        # Obtener objeto ExecutionInfo correspondiente a la instancia que se desea actualizar 
        ok = updateExecutionInstance(request.container_name, request.inter_parallelism, request.intra_parallelism, resources_availables)

        if(ok):
            print("Container: ",request.container_name," updated successfully")
            mutex_eventlogs.acquire()
            event_logs.save_event(events.ATTENTION_REQUEST_UP, thread_id, instance_number, request.intra_parallelism+request.inter_parallelism)
            mutex_eventlogs.release()
            state=1  
        else:
            print("Container is not running (abort update)")
            state=0
    
    return state

def updateExecutionInstance(container_name, new_inter_parallelism, new_intra_parallelism, resources_availables):
    
    # Buscar en la lista execInfo_list la instancia de ejecucion perteneciente al contenedor con nombre container_name y actualizar el paralelismo

    # En este momento system_info es thread-safe (desde attentionRequest)
    
    ok=False
    
    # realiza la búsqueda en la lista y obtiene el contenedor a actualizar
    mutex_execInfo.acquire()
    for x in execInfo_list:
        if x.getContainerName() == container_name:

            # Obtener los paralelismos de ejecucion del contenedor
            old_interParallelism= x.getInterExecution_parallelism()
            old_intraParallelism= x.getIntraExecution_parallelism()

            print('Old Parallelism: Inter=', old_interParallelism, ' - Intra=', old_intraParallelism, ' New Parallelism: Inter=', new_inter_parallelism, ' - Intra=', new_intra_parallelism)

            # Si es menor a cero quiere decir que vamos a decrementar el paralelismo total del contenedor
            if resources_availables<0:
                ok = x.updateParallelism(new_inter_parallelism, new_intra_parallelism)
                print("Free resources in container reassigment")
                ok=True
            else:
                parallelism_list= scheduler_container.schedule_parallelism(resources_availables, new_inter_parallelism-old_interParallelism, new_intra_parallelism-old_intraParallelism)
                if parallelism_list:
                    print("Parallelism Apply: ", parallelism_list[0] + parallelism_list[1])
                    ok = x.updateParallelism(old_interParallelism+parallelism_list[0] , old_intraParallelism+parallelism_list[1])
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
    
    return ok

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
            interUser_parallelism= container.getInterUser_parallelism()
            intraUser_parallelism= container.getIntraUser_parallelism()
            interparallelism_required= interUser_parallelism -  container.getInterExecution_parallelism()
            intraparallelism_required= intraUser_parallelism -  container.getIntraExecution_parallelism()
            if resources_availables >0:
                # Aumentar todo el paralelismo al contenedor
                if (interparallelism_required>0 and intraparallelism_required>0):
                    if resources_availables >= (interparallelism_required + intraparallelism_required):             
                        container.updateParallelism(interUser_parallelism, intraUser_parallelism)
                        print("Update total parallelism in container: ", container.getContainerName())
                        resources_availables= resources_availables-interparallelism_required-intraparallelism_required                       
                    else:
                        # Aumentar solo el intra paralelismo
                        if (resources_availables >= intraparallelism_required):
                            container.updateParallelism(intra_parallelism=intraUser_parallelism+intraparallelism_required)
                            resources_availables= resources_availables - intraparallelism_required
                            print("Update total intra parallelism in container: ", container.getContainerName(), " to: ", intraparallelism_required)
                        else:
                            container.updateParallelism(intra_parallelism=intraUser_parallelism+resources_availables) 
                            resources_availables=0
                            print("Update intra parallelism in container: ", container.getContainerName(), "to: ", intraUser_parallelism+resources_availables)
                        # Intentar aumentar el inter paralelismo con los recursos disponibles restantes (si es que hay)
                        if (resources_availables>0):
                            container.updateParallelism(inter_parallelism=interUser_parallelism+resources_availables)
                            resources_availables=0 
                            print("Update inter parallelism in container: ", container.getContainerName(), "to: ", interUser_parallelism+resources_availables)
                    ok=True
                else:
                    if(intraparallelism_required>0):
                        if (resources_availables >= intraparallelism_required):
                            container.updateParallelism(intra_parallelism=intraUser_parallelism+intraparallelism_required)
                            resources_availables= resources_availables - intraparallelism_required
                            print("Update total intra parallelism in container: ", container.getContainerName(), " to: ", intraparallelism_required)
                        else:
                            container.updateParallelism(intra_parallelism=intraUser_parallelism+resources_availables) 
                            resources_availables=0
                            print("Update intra parallelism in container: ", container.getContainerName(), "to: ", intraUser_parallelism+resources_availables)
                        ok=True
                    else:
                        if(interparallelism_required>0):
                            if (resources_availables >= interparallelism_required):
                                container.updateParallelism(inter_parallelism=interUser_parallelism+interparallelism_required)
                                resources_availables= resources_availables - interparallelism_required
                                print("Update total inter parallelism in container: ", container.getContainerName(), " to: ", interparallelism_required)
                            else:
                                container.updateParallelism(inter_parallelism=interUser_parallelism+resources_availables) 
                                resources_availables=0
                                print("Update inter parallelism in container: ", container.getContainerName(), "to: ", interUser_parallelism+resources_availables)
                            ok=True
            if ok:
                mutex_eventlogs.acquire()
                event_logs.save_event(events.REASSIGMENT_RESOURCES, thread_id, container.getContainerNumber(), container.getInterExecution_parallelism()+container.getIntraExecution_parallelism())
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

def generateExecutionRequest(thread_id):
    print('ExecutionRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)
    
    global finish_execution
    docker_image= 'tf_test'

    mutex_finishExecution.acquire()
    while not finish_execution:

        mutex_finishExecution.release()

        # Tiempo de espera para la próxima petición
        # Se utiliza distribución normal de tiempo con medio en 60 segundos y desviación estándar de 20 segundos
        normal_time = np.random.normal(loc=60, scale=20, size=1)
        time_wait= int(normal_time[0])

        # Preparar request con los datos necesarios:
        # -Paralelismo inter
        # -Paralelismo intra
        # -Nombre de archivo python
        # -Imagen docker 
        inter_parallelism = random.randint(1, 6)
        intra_parallelism = random.randint(1, 6)
        

        #Crear peticion 
        request_exec = Request(request_type="execution", container_name="null", docker_image=docker_image, inter_parallelism=inter_parallelism, intra_parallelism=intra_parallelism)
    
        #Comprobar scheduling de peticiones (con o sin prioridad)
        if priority_queue: 
            # Generar prioridad de peticion (0 = prioridad baja - 1 = prioridad media - 2 = prioridad alta)
            priority_request = random.randint(0, 2)

            # Almacenar peticion de ejecucion en la cola con prioridad
            # Ya es thread-safe la cola 
            q_priority_exec_update.put(priority_request, request_exec)
        else:
            # Almacenar la peticion en la cola sin prioridad
            # Ya es thread-safe la cola 
            q_normal_exec_update.put(request_exec)

        mutex_eventlogs.acquire()
        event_logs.save_event(events.GENERATE_REQUEST_EXE, thread_id, request_exec.inter_parallelism+request_exec.intra_parallelism)
        mutex_eventlogs.release()

        # Avisar al hilo de atencion que se encoló una nueva petición.
        with cv_attention:
            cv_attention.notify()
            print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)
        
        # Esperar un tiempo para realizar la siguiente petición
        time.sleep(time_wait)

        mutex_finishExecution.acquire()

    mutex_finishExecution.release()
    print("Finish execution request thread")

def generateUpdateRequest(thread_id):
    print('UpdateRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    # Cantidad de peticiones a realizar
    global finish_execution
    request_count = 0
    docker_image= 'tf_test'

    mutex_finishExecution.acquire()
    while not finish_execution:

        mutex_finishExecution.release()

        skip=False

        wait_containers=True

        while (wait_containers):
            with cv_update:
                # Esperar a que el hilo attentionRequest ejecute alguna instancia
                value=cv_update.wait()
                print('Wake up - Thread:', threading.current_thread().getName())
            if value:
                wait_containers=False
            else:
                print('Wait Timeout', threading.current_thread().getName())

        # Tiempo de espera para la próxima petición
        # Se utiliza distribución normal de tiempo con medio en 80 segundos y desviación estándar de 20 segundos
        normal_time = np.random.normal(loc=80, scale=20, size=1)
        time_wait= int(normal_time[0])
        print("Time Wait in Update Request: ",  time_wait)

        # Esperar un tiempo para realizar la siguiente petición
        time.sleep(time_wait) 

        try:
            # Preparar petición de actualización con los datos necesarios:
            # -Nombre del contenedor a actualizar
            # -Paralelismo inter
            # -Paralelismo intra
            mutex_containerList.acquire()
            container_name = random.choice(containerName_list)
            mutex_containerList.release()
        except: 
            print("Container not exist in List")
            skip=True
        
        if not skip:

            inter_parallelism = random.randint(1, 6)
            intra_parallelism = random.randint(1, 12)

            #Crear peticion de actualización 
            request_exec = Request(request_type="update", container_name= container_name, docker_image=docker_image,inter_parallelism=inter_parallelism, intra_parallelism=intra_parallelism)
        
            #Comprobar scheduling de peticiones (con o sin prioridad)
            if priority_queue: 
                # Generar prioridad de peticion (0 = prioridad baja - 1 = prioridad media - 2 = prioridad alta)
                priority_request = random.randint(0, 2)

                # Almacenar peticion de ejecucion en la cola con prioridad
                # Ya es thread-safe la cola 
                q_priority_exec_update.put(priority_request, request_exec)
            else:
                # Almacenar la peticion en la cola sin prioridad
                # Ya es thread-safe la cola 
                q_normal_exec_update.put(request_exec)

            mutex_eventlogs.acquire()
            event_logs.save_event(events.GENERATE_REQUEST_UP, thread_id, request_exec.container_name, request_exec.inter_parallelism+request_exec.intra_parallelism)
            mutex_eventlogs.release()
        
        mutex_finishExecution.acquire()
    mutex_finishExecution.release()
    print("Finish update request thread")

def container_client(clientsocket,addr,container_name, instance_number, interExec_parallelism, intraExec_parallelism, thread_id):

    container_eliminated= False

    # Enviar ID de cliente 
    clientsocket.send(bytes(str(instance_number), 'utf-8'))

    # Enviar comando TF de ejecución 
    #clientsocket.send(bytes(request.command, 'utf-8'))
    clientsocket.send(bytes(str(interExec_parallelism), 'utf-8'))
    clientsocket.send(bytes(str(intraExec_parallelism), 'utf-8'))

    msg=''

    loop=0

    # Esperar mensaje de finalización. 
    while not container_eliminated:

        try:
            # Recibir mensaje de finalización o problema del contenedor
            msg = clientsocket.recv(1024).decode('utf-8')
            if loop==0:
                print('Message recieved from Client ID: '+ str(instance_number)+" - Message: "+ msg)
            loop=loop+1
            #print (container_name, "send message: ", msg) (ver por qué recibe tantos mensajes vacios)
        except socket.timeout: # fail after 60 second of no activity
            print("Didn't receive data! [Timeout] - Container: " + str(instance_number))
        except socket.error as ex: 
            print("Connection reset by peer with request count=" + str(loop))
            print(ex)

        if msg == 'finalize':

            mutex_eventlogs.acquire()
            event_logs.save_event(events.FINISH_CONTAINER, thread_id, instance_number)
            mutex_eventlogs.release()

            # Buscar contenedor en la lista
            # Eliminar objeto contenedor de la lista de contenedores activos
            mutex_execInfo.acquire()
            for elem in execInfo_list:
                if (elem.container_name == container_name):
                    
                    # Encolar paralelismo liberado por el contenedor
                    q_finish_container.put(elem.getInterExecution_parallelism() + elem.getIntraExecution_parallelism())
                    print("Push Free Parallelism of Container: ", container_name, " Parallelism: ", elem.getInterExecution_parallelism() + elem.getIntraExecution_parallelism())

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
            containerName_list.remove(container_name)
            mutex_containerList.release()

            # Informar en caso de que no se pueda eliminar el contenedor
            if not container_eliminated:
                print('The container ', container_name, ' could not be deleted')
            else: 
                # Enviar ACK indicando finalizacion de la eliminacion del cliente
                print("Send ACK to client: " + str(instance_number))
                clientsocket.send(bytes('f', 'utf-8'))
    print("Finish Client Thread - Container: ", instance_number)

def attentionRequest(socket_schedule, thread_id):
    print('AttentionRequest Thread:', threading.current_thread().getName())

    instance_number=0
    request_pending=False
    port_host=8787
    global q_request_pending
    global finish_execution
    mutex_finishExecution.acquire()
    
    while not finish_execution:

        mutex_finishExecution.release()

        with cv_attention:
            # Esperar a que alguno de los demas hilos avise que hay peticiones pendientes (ejecución, actualización o eliminación de contenedores)
            cv_attention.wait()
            print('Wake up:', threading.current_thread().getName())

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
        while ((resources_availables>0) and (not q_request_pending.empty())):
            request= q_request_pending.get()

            # Definirlo como método# (se usa dos veces)
            if (request.request_type=='update'):
                # Buscar contenedor y obtener la cantidad de recusos solicitados
                mutex_execInfo.acquire()
                for x in execInfo_list:
                    if x.getContainerName() == request.container_name:
                        requested_resources= (request.inter_parallelism+request.intra_parallelism) - (x.getInterUser_parallelism()+x.getIntraUser_parallelism())                
                mutex_execInfo.release()
            else:
                # Obtener los recursos solicitados por la peticion de ejecucion 
                requested_resources=request.inter_parallelism+request.intra_parallelism

            if ((requested_resources>0) and (requested_resources <= resources_availables)):
                # Decrementar la cantidad de recursos disponibles 
                system_info.apply_resources(requested_resources)
            else: 
                if(requested_resources>0):
                    # Quiere decir que es una peticion de incremento de recursos y no alcanza la cantidad recursos disponibles. Probar si la politica de planificacion acepta una peticion con esta cantidad de recursos.
                    # Decrementar la cantidad de recursos disponibles 
                    system_info.apply_resources(resources_availables)
                    requested_resources=resources_availables
                else:
                    # En caso de que el total del paralelismo se disminuya (en este caso nunca sera verdadero pero si se quiere modularizar hay que ponerlo)
                    system_info.free_resources(-requested_resources)
            # Fin de método#

            mutex_systemInfo.release()

            # Intentar planificar peticion pendiente       
            state= schedule_request(request, socket_schedule, instance_number, port_host, requested_resources, thread_id)

            mutex_systemInfo.acquire()
            if state==0:
                print ("Pending petition could not be answered")
                q_aux.put(request)
                system_info.free_resources(requested_resources)
            else:
                if request.request_type=="execution":
                    instance_number=instance_number+1
                    port_host= port_host+1   
                    with cv_update:
                        cv_update.notify()
            resources_availables= system_info.check_resources()
            print("Resources availables after schedule: " + str(resources_availables)) 
        mutex_systemInfo.release()

        # Almacenar las peticiones antiguas pendientes en la cola nuevamente
        if (not q_aux.empty()):
            q_request_pending=q_aux

        print('Attention new act/exe request: ',threading.current_thread().getName())

        # Intentar atender nuevas peticiones de ejecucion/actualizacion
        mutex_systemInfo.acquire()
        resources_availables= system_info.check_resources()
        finish_schedule_queue=False
        while ((resources_availables > 0) and ((not q_normal_exec_update.empty()) or (not q_priority_exec_update.empty()))):
            if priority_queue:
                print('Serve queue act / exe requests with priority : ',threading.current_thread().getName())
                if not q_priority_exec_update.empty():
                    request = q_priority_exec_update.get()
            else:
                print('Serve queue act / exe requests without priority : ',threading.current_thread().getName())
                if not q_normal_exec_update.empty():
                    request = q_normal_exec_update.get()
            
            # Definirlo como método# (se usa dos veces)
            if (request.request_type=='update'):
                # Buscar contenedor y obtener la cantidad de recusos solicitados
                for x in execInfo_list:
                    if x.getContainerName() == request.container_name:
                        requested_resources= (request.inter_parallelism+request.intra_parallelism) - (x.getInterUser_parallelism()+x.getIntraUser_parallelism())
            else:
                # Obtener los recursos solicitados por la peticion de ejecucion 
                requested_resources=request.inter_parallelism+request.intra_parallelism

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
            # Fin de método a implementar#
            
            mutex_systemInfo.release()

            if (request.request_type=='update'):
                print('Schedule request:', request.request_type,' Container:', request.container_name, ' Inter-Parallelism:', request.inter_parallelism, ' Intra-Parallelism:', request.intra_parallelism, ' Thread-ID:', threading.current_thread().getName())  
            else:
                print('Schedule request:', request.request_type,' Inter-Parallelism:', request.inter_parallelism, ' Intra-Parallelism:', request.intra_parallelism, ' Thread-ID:', threading.current_thread().getName()) 
            
            state= schedule_request(request, socket_schedule, instance_number, port_host, requested_resources, thread_id)  

            # Verificar si no se pudo atender la peticion
            if (state==0):
                # Verificar si la cantidad de paralelismo solicitada excede el máximo de la máquina
                if((request.inter_parallelism+request.intra_parallelism)>system_info.total_cores()):
                    print("Request discarded because the parallelism requested exceeds the maximum number of cores of the machine")
                else:
                    print("Request pending")
                    q_request_pending.put(request)
                system_info.free_resources(requested_resources)
            else: 
                # Avisar al hilo generador de peticiones de actualización cuando se crea una instancia Docker
                if request.request_type =='execution':
                    instance_number=instance_number+1
                    port_host= port_host+1   
                    with cv_update:
                        cv_update.notify() 

            mutex_systemInfo.acquire()
            resources_availables= system_info.check_resources()
            print("Resources availables after schedule: " + str(resources_availables))   
        mutex_systemInfo.release() 

        mutex_finishExecution.acquire()
    
    mutex_finishExecution.release()

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
    number_thread= number_thread+1

    # Crear hilo para la generacion de peticiones de ejecución
    request_thread = threading.Thread(target=generateExecutionRequest, args=(number_thread,))
    number_thread=number_thread+1

    # Crear hilo para la generacion de peticiones de actualización de paralelismo de contenedores
    update_thread = threading.Thread(target=generateUpdateRequest, args=(number_thread,))
    number_thread=number_thread+1
    
    # Iniciar todos los hilos
    attention_thread.start()
    request_thread.start()
    update_thread.start()

    # Esperar la terminación de los hilos
    attention_thread.join()
    request_thread.join()
    update_thread.join()

    # Esperar la terminacion de los hilos clientes
    while not client_threads.empty():
        client= client_threads.get()
        client.join()

    socket_schedule.close()

    event_logs.save_CSV('./Data/log/', 'scheduler_events.txt')
    event_logs.plot_events()

# Fin de Programa Principal #