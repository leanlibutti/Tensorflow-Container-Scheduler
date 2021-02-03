import os
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
from trace import TraceLog
from system import systemInfo
from scheduling_policy import FFSnotReassignment, FFSReassignment

#Mutex para acceder al trace log
mutex_eventlogs= threading.Lock()

# Almacena la informacion de los eventos en el planificador
event_logs= TraceLog(12)

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

# Métodos Generales #

def updateExecutionInstance(container_name, new_inter_parallelism, new_intra_parallelism):
    
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

            # Setear paralelismos enviados por el usuario para actualizar
            x.setInterUser_parallelism(new_inter_parallelism)
            x.setIntraUser_parallelism(new_intra_parallelism)

            print('Old Parallelism: Inter=', old_interParallelism, ' - Intra=', old_intraParallelism, ' New Parallelism: Inter=', new_inter_parallelism, ' - Intra=', new_intra_parallelism)

            if (new_inter_parallelism>old_interParallelism):
                if(new_intra_parallelism > old_intraParallelism):
                    # se van a incrementar ambos paralelismos
                    parallelism_list= scheduler_container.schedule_parallelism(system_info, new_inter_parallelism-old_interParallelism, new_intra_parallelism-old_intraParallelism)
                    if parallelism_list:
                        parallelism_apply=parallelism_list[0]-old_interParallelism+parallelism_list[1]-old_intraParallelism
                        print("Parallelism Apply: ", parallelism_apply)
                        if system_info.apply_resources(parallelism=parallelism_apply):
                            print("Increment both parallelisms: ", new_inter_parallelism, ' - ', new_intra_parallelism)
                            ok = x.updateParallelism(new_inter_parallelism, new_intra_parallelism)
                        else:
                            print("Error: not update intra and inter parallelism in container:", x.getContainerName())
                else:
                    # solo se incrementa el paralelismo inter
                    parallelism_list=scheduler_container.schedule_parallelism(system_info,new_inter_parallelism-old_interParallelism, 0)
                    parallelism_apply= parallelism_list[0]-old_interParallelism+(old_intraParallelism-new_intra_parallelism)
                    print("Parallelism Apply: ", parallelism_apply)
                    if(system_info.apply_resources(parallelism=parallelism_apply)):
                        print("Only increment inter parallelism: ", new_inter_parallelism)
                        ok = x.updateParallelism(new_inter_parallelism, new_intra_parallelism)
                    else:
                        print("Error: not update inter parallelism in container:", x.getContainerName())
            else:
                if new_intra_parallelism>old_intraParallelism:
                    # solo se incrementa el paralelismo intra
                    parallelism_list=scheduler_container.schedule_parallelism(system_info,0, new_intra_parallelism-old_intraParallelism)
                    parallelism_apply=parallelism_list[1]-old_intraParallelism+(old_interParallelism-new_inter_parallelism)
                    if(system_info.apply_resources(parallelism=parallelism_apply)):
                        print("Only increment intra parallelism: ", new_intra_parallelism)
                        ok = x.updateParallelism(new_inter_parallelism, new_intra_parallelism)
                    else:
                        print("Error: not update intra parallelism in container:", x.getContainerName())
                else:
                    # se disminuyen ambos paralelismos
                    system_info.free_resources(old_interParallelism-new_inter_parallelism+old_intraParallelism-new_intra_parallelism)
                    print("Decrement both parallelisms: ", new_inter_parallelism, ' - ', new_intra_parallelism)
                    ok = x.updateParallelism(new_inter_parallelism, new_intra_parallelism)
    mutex_execInfo.release()
    
    return ok

def attentionSignal(num, frame):
    pass

# Fin Métodos Generales #

# Métodos asignados a hilos #

def generateExecutionRequest():
    print('ExecutionRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    # Cantidad de peticiones a realizar
    request_count = 0

    docker_image= 'tf_malleable'

    while request_count < 10:

        # Tiempo de espera para la próxima petición
        # Se utiliza distribución normal de tiempo con medio en 30 segundos y desviación estándar de 5 segundos
        normal_time = np.random.normal(loc=30, scale=5, size=1)
        time_wait= int(normal_time[0])

        # Preparar request con los datos necesarios:
        # -Paralelismo inter
        # -Paralelismo intra
        # -Nombre de archivo python
        # -Imagen docker 
        inter_parallelism = random.randint(1, 6)
        intra_parallelism = random.randint(1, 12)
        

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
        event_logs.save_event(3, threading.current_thread().ident, 0)
        mutex_eventlogs.release()

        # Avisar al hilo de atencion que se encoló una nueva petición.
        with cv_attention:
            cv_attention.notify()
            print('Send notify, Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)
        
        # Esperar un tiempo para realizar la siguiente petición
        time.sleep(time_wait)

def generateUpdateRequest():
    print('UpdateRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    # Cantidad de peticiones a realizar
    request_count = 0

    docker_image= 'tf_malleable'

    while request_count < 5:
        
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
        # Se utiliza distribución normal de tiempo con medio en 20 segundos y desviación estándar de 5 segundos
        normal_time = np.random.normal(loc=20, scale=5, size=1)
        time_wait= int(normal_time[0])
        print("Time Wait in Update Request: ",  time_wait)

        # Esperar un tiempo para realizar la siguiente petición
        time.sleep(time_wait) 

        # Preparar petición de actualización con los datos necesarios:
        # -Nombre del contenedor a actualizar
        # -Paralelismo inter
        # -Paralelismo intra
        mutex_containerList.acquire()
        container_name = random.choice(containerName_list)
        mutex_containerList.release()
    
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
        event_logs.save_event(4, threading.current_thread().ident, 0)
        mutex_eventlogs.release()

def container_client(clientsocket,addr,container_name, instance_number, interExec_parallelism, intraExec_parallelism):

    container_eliminated= False

    # Enviar ID de cliente 
    clientsocket.send(bytes(str(instance_number), 'utf-8'))

    # Enviar comando TF de ejecución 
    #clientsocket.send(bytes(request.command, 'utf-8'))
    clientsocket.send(bytes(str(interExec_parallelism), 'utf-8'))
    clientsocket.send(bytes(str(intraExec_parallelism), 'utf-8'))

    # Esperar mensaje de finalización. 
    while not container_eliminated:

        try:
            # Recibir mensaje de finalización o problema del contenedor
            msg = clientsocket.recv(1024).decode('utf-8')
            #print (container_name, "send message: ", msg) (ver por qué recibe tantos mensajes vacios)
        except socket.timeout: # fail after 60 second of no activity
            print("Didn't receive data! [Timeout]")

        if msg == 'finalize':

            mutex_eventlogs.acquire()
            event_logs.save_event(5, threading.current_thread().ident, 0)
            mutex_eventlogs.release()

            # Buscar contenedor en la lista
            # Eliminar objeto contenedor de la lista de contenedores activos
            mutex_execInfo.acquire()
            for elem in execInfo_list:
                if (elem.container_name == container_name):
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

    # Cerrar conexión con el contenedor cliente
    clientsocket.close()

# System Info Safe
def oldest_reassigment(resources_availables, increase_or_reduce, amount_reduce=0):

    if increase_or_reduce:
        mutex_execInfo.acquire()
        for container in execInfo_list:
            interUser_parallelism= container.getInterUser_parallelism()
            intraUser_parallelism= container.getIntraUser_parallelism()
            interparallelism_required= interUser_parallelism -  container.getInterExecution_parallelism()
            intraparallelism_required= intraUser_parallelism -  container.getIntraExecution_parallelism()
            if resources_availables >= (interparallelism_required + intraparallelism_required):             
                if system_info.apply_resources(interparallelism_required + intraparallelism_required):
                    container.updateParallelism(interUser_parallelism, intraUser_parallelism)
                else: 
                    print("Not update total parallelism in container: ", container.getContainerName())          
            else:
                if resources_availables >= intraparallelism_required:
                    if system_info.apply_resources(intraparallelism_required):
                        container.updateParallelism(intra_parallelism=intraUser_parallelism)
                        resources_availables= resources_availables - intraparallelism_required
                    else:
                        print("Not update total intra parallelism in container: ", container.getContainerName())
                        if system_info.apply_resources(resources_availables):
                            print("update intra parallelism to: ", intraUser_parallelism+resources_availables)
                            container.updateParallelism(intra_parallelism=intraUser_parallelism+resources_availables) 
                            resources_availables=0
                if resources_availables >= interparallelism_required:
                    if system_info.apply_resources(intraparallelism_required):
                        container.updateParallelism(inter_parallelism=interUser_parallelism)
                    else:
                        print("Not update total inter parallelism in container: ", container.getContainerName())
                        if system_info.apply_resources(resources_availables):
                            print("update inter parallelism to: ", interUser_parallelism+resources_availables)
                            container.updateParallelism(intra_parallelism=intraUser_parallelism+resources_availables) 
            resources_availables= system_info.check_resources()
            if resources_availables == 0:
                break
            mutex_execInfo.release()
        else:
            # reducir el paralelismo de los contenedores mas viejo liberando la cantidad de recursos solicitados (amount_reduce)
            pass

def schedule_request(request, socket_schedule, instance_number=0):

    port= 8787

    if request.request_type == 'execution':

        print('Schedule Execution Request: ',threading.current_thread().getName())

        parallelism_container= scheduler_container.schedule_parallelism(system_info, request.inter_parallelism, request.intra_parallelism)

        # Accede a consultar si hay paralelismo disponible (system_info es thread-safe en este momento)
        if parallelism_container:
        
            # Atender petición de ejecución
            container_name= 'instance' + str(instance_number)
            
            # Comando para iniciar contenedor con una imagen dada en la petición (opciones dit permiten dejar ejecutando el contenedor en background)
            print("Creating Docker Container...")

            #docker_command= 'docker run -dit --name '+ container_name + ' -p ' + str(port) + ':8787 --volume /var/run/docker.sock:/var/run/docker.sock ' + request.docker_image 
            docker_command= 'docker run -dit --name '+ container_name + ' -p ' + str(port) + ':8787 --volume /home/leandro/Documentos/Data:/home/Data ' + request.docker_image 
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
                    tmp_thread = threading.Thread(target=container_client, args=(c,addr,container_name, instance_number, parallelism_container[0], parallelism_container[1],))
                    tmp_thread.start()
                except socket.timeout:
                    print("Connection establish timeout")
                    attemps= attemps+1
                    if attemps == 5:
                        print("Could not create docker container")
                    pass
            
            if attemps != 5:

                mutex_eventlogs.acquire()
                event_logs.save_event(1, threading.current_thread().ident, 0)
                mutex_eventlogs.release()

                #Transformar stdout en container ID
                container_id =  stdout[:12]
                
                # almacenar ID del proceso
                process_id_command= 'docker container top ' + container_id + ' -o pid'
                process_command = Popen([process_id_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
                stdout, stderr = process_command.communicate()

                #Transformar la salida de stdout en process ID 
                # Salida del tipo:
                # PID
                # 4483   
                # Me quedo con la parte de abajo de la salida (si tiene hasta 4 dígitos el PID, sino ver cómo solucionar)
                process_id = stdout[4:8] 

                if(len(stderr)):
                    print(stderr)
                else:
                    print('Name of request: ', container_name, ' - Container ID: ', container_id, 'Container Process ID: ', process_id)

                # Crear un ExecutionInfo para almacenar la informacion de la instancia ejecutada
                exec_info = ExecutionInfo(container_name, port, process_id, request.inter_parallelism, request.intra_parallelism, parallelism_container[0], parallelism_container[1], c)

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

        print('Schedule Update Request: ',threading.current_thread().getName())

        # Obtener objeto ExecutionInfo correspondiente a la instancia que se desea actualizar 
        ok = updateExecutionInstance(request.container_name, request.inter_parallelism, request.intra_parallelism)

        if(ok):
            print("Container: ",request.container_name," updated successfully")
            mutex_eventlogs.acquire()
            event_logs.save_event(2, threading.current_thread().ident, 0)
            mutex_eventlogs.release()
            state=1
        else:
            print("Container is not running (abort update)")
            state=0
    
    return state

def attentionRequest(socket_schedule):
    print('AttentionRequest Thread:', threading.current_thread().getName())

    instance_number=0

    request_pending=False
    
    while True:

        with cv_attention:
            # Esperar a que alguno de los demas hilos avise que hay peticiones pendientes (ejecución, actualización, replanificación o eliminación de contenedores)
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
            if resources_availables>0: 
                oldest_reassigment(resources_availables, True)
                mutex_eventlogs.acquire()
                event_logs.save_event(6, threading.current_thread().ident, 0)
                mutex_eventlogs.release()
            mutex_systemInfo.release()

        print('Attention act/exe request: ',threading.current_thread().getName())

        mutex_systemInfo.acquire()
        resources_availables= system_info.check_resources()
        while (resources_availables > 0) and ((not q_normal_exec_update.empty()) or (not q_priority_exec_update.empty())):
            # Atender petición de ejecución/actualización
            if not request_pending:
                if priority_queue:
                    print('Serve queue act / exe requests with priority : ',threading.current_thread().getName())
                    if not q_priority_exec_update.empty():
                        request = q_priority_exec_update.get()
                else:
                    print('Serve queue act / exe requests without priority : ',threading.current_thread().getName())
                    if not q_normal_exec_update.empty():
                        request = q_normal_exec_update.get()
            resources_availables= system_info.check_resources() 
            print('Schedule act/exe request: ',threading.current_thread().getName())
            state= schedule_request(request, socket_schedule, instance_number)
            resources_availables= system_info.check_resources()
            
            # Verificar si no se pudo atender la peticion
            if (state==0):
                # Verificar si la cantidad de paralelismo solicitada no excede el máximo de la máquina
                if((request.inter_parallelism+request.intra_parallelism)<system_info.total_cores()):
                    request_pending= True
                else:
                    print("Request discarded because the parallelism requested exceeds the maximum number of cores of the machine")
            else: 
                # Avisar al hilo generador de peticiones de actualización cuando se crea una instancia Docker
                with cv_update:
                    cv_update.notify() 
                request_pending=False
        mutex_systemInfo.release() 
'''
def deletionInstances():

    print('Deletion Instances Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    # Registrar callback
    signal.signal(10, attentionSignal)

    print("I'm %d, talk to me with 'kill -10 %d'" % (os.getpid(),os.getpid()))

    # Atención de señales enviadas por las instancias TF cuando terminan su ejecución
    while True:
        siginfo = signal.sigwaitinfo({10})
        print("Instance with process id: %d by user %d\n" % (siginfo.si_pid, siginfo.si_uid))

'''      
# Fin Métodos asignados a hilos #

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

    print("Creating threads...")

    # Crear hilo para la atención de solicitudes
    attention_thread = threading.Thread(target=attentionRequest, args=(socket_schedule,))

    # Crear hilo para la generacion de peticiones de ejecución
    request_thread = threading.Thread(target=generateExecutionRequest)

    # Crear hilo para la generacion de peticiones de actualización de paralelismo de contenedores
    update_thread = threading.Thread(target=generateUpdateRequest)
    
    # Iniciar todos los hilos
    attention_thread.start()
    request_thread.start()
    update_thread.start()

    # Esperar la terminación de los hilos
    attention_thread.join()
    request_thread.join()
    update_thread.join()
