import os
import threading 
import random
import queue
import time
from collections import namedtuple
from subprocess import Popen, PIPE, STDOUT

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
    def updateExecution(inter_parallelism, intra_parallelism):
        # Nuevo paralelismo total soportado por el contenedor
        new_parallelism= inter_parallelism + intra_parallelism

        # Comando de actualización del paralelismo del contenedor
        run_command= 'docker update ' + self.docker_ps + ' --cpus ' + new_parallelism
        
        if inter_parallelism != self.inter_parallelism:
            # Setear las variable de entorno correspondiente al paralelismo inter de la instancia de Tensorflow actual
            os.environ["INTER_PARALELLISM"] = inter_parallelism
       
            # Enviar señal que sera capturada por la instancia de Tensorflow dentro del contenedor
            os.kill(docker_ps, 10) # verificar si es esa señal

        if intra_parallelism != self.intra_parallelism:
            # Setear las variable de entorno correspondiente al paralelismo inter de la instancia de Tensorflow actual
            os.environ["INTRA_PARALELLISM"]  = intra_parallelism 
       
            # Enviar señal que sera capturada por la instancia de Tensorflow dentro del contenedor
            os.kill(docker_ps, 12) # verificar si es esa señal

        # Actualizar paralelismo del contenedor
        os.system(run_command)

        print("Updated parallelism for container: ", self.container_name, " - Inter Parallelism: ", inter_parallelism, " Intra Parallelism: ", intra_parallelism)

    # Retorna el nombre del contenedor de la instancia TF en ejecución
    def getContainerName(self):
        return self.container_name

# Lista que almacena la información de cada instancia de TF que se encuentra en ejecución
execInfo_list=[]

def generateList():

    i=5
    instancia=0
    for i in range(i):
        
        container_name="instancia"+str(instancia) 

        print("Nombre de Contenedor: ", container_name)
        
        # Crear un ExecutionInfo para almacenar la informacion de la instancia ejecutada
        exec_info = ExecutionInfo(container_name, 8787, 1234, "el pepe", 1, 4)

        # Almacenar instancia de execución en la lista de ejecuciones activas (es thread safe)
        execInfo_list.append(exec_info)

        instancia= instancia + 1


def searchExecutionInfo(container_name):
    # Buscar en la lista execInfo_list la instancia de ejecucion perteneciente al contenedor con nombre container_name
    
    # realiza la búsqueda en la lista y retorna una lista solo con el elemento buscado o vacia si no se encuentra
    search_list = [x for x in execInfo_list if x.getContainerName() == container_name]

    if len(search_list)>0:
        # Retorna el objeto ExecutionInfo correspondiente al container name recibido por parámetro
        execInfo_list.remove(search_list[0])
        return search_list[0]
    else:
        return None

def printList():
    print("##Lista##")
    for i in range(len(execInfo_list)):
        print("Contenedor ", execInfo_list[i].container_name)
    print("#########")
if __name__ == "__main__":

    generateList()

    print("Dimension de la lista antes de la busqueda: ", len(execInfo_list))

    printList()

    instance_info= searchExecutionInfo("instancia3")

    print("Dimension de la lista luego de la busqueda: ", len(execInfo_list))

    printList()

    print("Nombre del contenedor devuelto: ", instance_info.container_name)

    process_id_command= 'docker images'
    
    process_command = Popen([process_id_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    stdout, stderr = process_command.communicate()

    print(stdout)
    print(stderr)
    print(len(stdout))
    print(len(stderr))
