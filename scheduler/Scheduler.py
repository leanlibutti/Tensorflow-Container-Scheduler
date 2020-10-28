import os
import threading 
import random
import queue
import time
from collections import namedtuple
from subprocess import Popen, PIPE, STDOUT
import signal

# Clase que contiene la información asociada a una instancia de ejecución de Tensorflow
class ExecutionInfo:
    def __init__(self, container_name, container_port, docker_ps, command_tf, inter_parallelism, intra_parallelism):
        self.container_name = container_name
        self.docker_ps = docker_ps
        self.command = command_tf
        self.inter_parallelism = inter_parallelism
        self.intra_parallelism = intra_parallelism
        self.container_port = container_port

    # Actualizar el paralelismo total del contenedor en ejecución
    # Retorna si la operacion de actualización se pudo realizar correctamente
    def updateParallelism(self, inter_parallelism, intra_parallelism):
        # Nuevo paralelismo total soportado por el contenedor
        new_parallelism= inter_parallelism + intra_parallelism

        # Comando de actualización del paralelismo del contenedor
        run_command= 'docker update ' + self.docker_ps + ' --cpus ' + new_parallelism
        
        if inter_parallelism != self.inter_parallelism:
            # Setear las variable de entorno correspondiente al paralelismo inter de la instancia de Tensorflow actual
            os.environ["INTER_PARALELLISM"] = inter_parallelism

            kill_command= "docker kill --signal=10 " + docker_ps # verificar si es esa señal (numero 10)
       
            # Enviar señal que sera capturada por la instancia de Tensorflow dentro del contenedor
            process_command = Popen([kill_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()

            if (len(stderr)):
                print(stderr)
                return False

        if intra_parallelism != self.intra_parallelism:
            # Setear las variable de entorno correspondiente al paralelismo inter de la instancia de Tensorflow actual
            os.environ["INTRA_PARALELLISM"]  = intra_parallelism 
       
             
            kill_command= "kill -12 " + docker_ps # verificar si es esa señal
            
            # Enviar señal que sera capturada por la instancia de Tensorflow dentro del contenedor
            process_command = Popen([kill_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()

            if (len(stderr)):
                print(stderr)
                return False

        # Actualizar paralelismo del contenedor
        process_command = Popen([run_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        stdout, stderr = process_command.communicate()

        if (len(stderr)):
            print(stderr)
            return False
        else:
            print("Updated parallelism for container: ", self.container_name, " - Inter Parallelism: ", inter_parallelism, " Intra Parallelism: ", intra_parallelism)
            return True

    # Retorna el nombre del contenedor de la instancia TF en ejecución
    def getContainerName(self):
        return self.container_name

#Indica si las peticiones de ejecucion se manejan con prioridad o no
priority_queue = False

# Cola sin prioridad para almacenar peticiones de ejecucion y actualizacion 
q_normal = queue.Queue(10)

# Cola con prioridad que puede almacenar hasta 10 peticiones de ambos tipos (ejecución y actualización)
# Si se desea colocar cuando está llena se realiza un bloqueo hasta que haya lugar
q_priority = queue.PriorityQueue(10)

# Crear estructura de petición (namedtuple) con los siguientes datos:
# - Tipo de peticion (nueva ejecucion o actualizar paralelismo)
# - Comando de sistema a ejecutar
# - Paralelismo Inter
# - Paralelismo Intra
Request = namedtuple('Request', ['request_type', 'container_name', 'docker_image', 'command', 'inter_parallelism', 'intra_parallelism'])

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

def updateExecutionInstance(container_name, inter_parallelism, intra_parallelism):
    
    # Buscar en la lista execInfo_list la instancia de ejecucion perteneciente al contenedor con nombre container_name y actualizar el paralelismo
    
    ok=False
    
    # realiza la búsqueda en la lista y actualiza el paralelismo de la instancia TF (con EC?)
    mutex_execInfo.acquire()
    for x in execInfo_list:
        if x.getContainerName() == container_name:
            ok = x.updateParallelism(inter_parallelism, intra_parallelism)

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

    # Nombre del archivo python que contiene el codigo TF a ejecutar
    python_archive = 'ejemplo.py'

    while request_count < 10:

        # Tiempo de espera para la próxima petición
        # Se utiliza distribución normal de tiempo con medio en 10 segundos y desviación estándar de 2 segundos
        time_wait = random.normal(loc=10, scale=2, size=1)

        # Preparar request con los datos necesarios:
        # -Paralelismo inter
        # -Paralelismo intra
        # -Nombre de archivo python
        # -Imagen docker 
        inter_parallelism = random.randint(1, 6)
        intra_parallelism = random.randint(1, 12)
        command = 'python3 ' + archive + ' ' + str(inter) + ' ' + str(intra)
        docker_image= 'tf-malleable'

        #Crear peticion 
        request_exec = Request(request_type="execution", docker_image=docker_image, command=command, inter_parallelism=inter_parallelism, intra_parallelism=intra_parallelism)
    
        #Comprobar scheduling de peticiones (con o sin prioridad)
        if priority_queue: 
            # Generar prioridad de peticion (0 = prioridad baja - 1 = prioridad media - 2 = prioridad alta)
            priority_request = random.randint(0, 2)

            # Almacenar peticion de ejecucion en la cola con prioridad
            # Ya es thread-safe la cola 
            q_priority.put(priority_request, request_exec)
        else:
            # Almacenar la peticion en la cola sin prioridad
            # Ya es thread-safe la cola 
            q_normal.put(request_exec)
        
        # Esperar un tiempo para realizar la siguiente petición
        time.sleep(time_wait)

def generateUpdateRequest():
    print('UpdateRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

    # Cantidad de peticiones a realizar
    request_count = 0

    while request_count < 5:

        # Esperar a que el hilo attentionRequest ejecute alguna instancia
        cv_update.wait()

        # Tiempo de espera para la próxima petición
        # Se utiliza distribución normal de tiempo con medio en 10 segundos y desviación estándar de 2 segundos
        time_wait = random.normal(loc=10, scale=2, size=1)

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
        request_exec = Request(request_type="update", container_name= container_name, inter_parallelism=inter_parallelism, intra_parallelism=intra_parallelism)
    
        #Comprobar scheduling de peticiones (con o sin prioridad)
        if priority_queue: 
            # Generar prioridad de peticion (0 = prioridad baja - 1 = prioridad media - 2 = prioridad alta)
            priority_request = random.randint(0, 2)

            # Almacenar peticion de ejecucion en la cola con prioridad
            # Ya es thread-safe la cola 
            q_priority.put(priority_request, request_exec)
        else:
            # Almacenar la peticion en la cola sin prioridad
            # Ya es thread-safe la cola 
            q_normal.put(request_exec)
        
        # Esperar un tiempo para realizar la siguiente petición
        time.sleep(time_wait)


def attentionRequest():
    print('AttentionRequest Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)
    instance_number=0
    port= 8787
    while True:
        if priority_queue:
            # Sacar petición de la cola con prioridad
            # Ya es thread-safe la cola 
            request = q_priority.get()
        else:
            # Sacar petición de la cola sin prioridad
            # Ya es thread-safe la cola 
            request = q_normal.get()

        if request.request_type == 'execution':
            
            # Atender petición de ejecución
            container_name= 'instance' + instance_number
            instance_number+=1

            # Comando para iniciar contenedor con una imagen dada en la petición (opciones dit permiten dejar ejecutando el contenedor en background)
            docker_command= 'docker run -dit --name '+ container_name + ' -p ' + port + ':8787 ' + request.docker_image 
            
            # Ejecutar comando (con os.p)
            # Los primeros 12 caracteres de stdout son el container ID
            process_command = Popen([docker_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            stdout, stderr = process_command.communicate()

            #Transformar stdout en container ID
            container_id =  stdout[:12]
            
            # almacenar ID del proceso
            process_id_command= 'docker container top' + container_id + '-o pid'
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
            exec_info = ExecutionInfo(container_name, port, process_id, request.command, request.inter_parallelism, request.intra_parallelism)

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
                cv_update.notify()
        else:
            # Atender petición de actualización

            # Obtener objeto ExecutionInfo correspondiente a la instancia que se desea actualizar 
            ok = updateExecutionInstance(request.container_name, request.inter_parallelism, request.intra_parallelism)

            if(ok):
                print("Container: ",request.container_name," updated successfully")
            else:
                print("Container is not running (abort update)")

    def deletionInstances():

        print('Deletion Instances Thread:', threading.current_thread().getName(), ' - ID:', threading.current_thread().ident)

        # Registrar callback
        signal.signal(10, attentionSignal)

        print("I'm %d, talk to me with 'kill -10 %d'" % (os.getpid(),os.getpid()))

        # Atención de señales enviadas por las instancias TF cuando terminan su ejecución
        while True:
            siginfo = signal.sigwaitinfo({10})
            print("Instance with process id: %d by user %d\n" % (siginfo.si_pid, siginfo.si_uid))

        
# Fin Métodos asignados a hilos #

if __name__ == "__main__":

    print("Scheduler for Instances TF")
    print("Creating threads...")
