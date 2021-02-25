from Commons import json_data_socket

# Clase que contiene la información asociada a una instancia de ejecución de Tensorflow
class ExecutionInfo:
    def __init__(self, container_name, container_number, container_port, docker_ps, interUser_parallelism, intraUser_parallelism, interExecution_parallelism, intraExecution_parallelism, clientsocket):
        self.container_name = container_name
        self.docker_ps = docker_ps
        self.interUser_parallelism = interUser_parallelism
        self.intraUser_parallelism = intraUser_parallelism
        self.intraExecution_parallelism = intraExecution_parallelism
        self.interExecution_parallelism = interExecution_parallelism
        self.container_port = container_port
        self.clientsocket = clientsocket
        self.container_number=container_number

    def getInterUser_parallelism(self):
        return self.interUser_parallelism
    
    def getIntraUser_parallelism(self):
        return self.intraUser_parallelism

    def getInterExecution_parallelism(self):
        return self.interExecution_parallelism
        
    def getIntraExecution_parallelism(self):
        return self.intraExecution_parallelism
    
    def setInterUser_parallelism(self, new_interUser_parallelism):
        self.interUser_parallelism = new_interUser_parallelism

    def setIntraUser_parallelism(self, new_intraUser_parallelism):
        self.intraUser_parallelism = new_intraUser_parallelism

    def setInterExecution_parallelism(self, new_interExec_parallelism):
        self.interExecution_parallelism = new_interExec_parallelism
    
    def setIntraExecution_parallelism(self, new_intraExec_parallelism):
        self.interExecution_parallelism = new_intraExec_parallelism

    # Retorna el nombre del contenedor de la instancia TF en ejecución
    def getContainerName(self):
        return self.container_name

    def getContainerNumber(self):
        return self.container_number

    # Actualizar el paralelismo total del contenedor en ejecución
    # Retorna si la operacion de actualización se pudo realizar correctamente
    def updateParallelism(self, inter_parallelism=0, intra_parallelism=0):
        # Nuevo paralelismo total soportado por el contenedor
        new_parallelism= inter_parallelism + intra_parallelism
        # Comando de actualización del paralelismo del contenedor
        run_command= 'docker update ' + str(self.docker_ps) + ' --cpus ' + str(new_parallelism)    
        # Generar objeto JSON para enviar actualizacion
        data= {
            "container": self.container_number,
            "inter_parallelism": inter_parallelism,
            "intra_parallelism": intra_parallelism
        }  
        # Enviar objeto JSON al cliente
        json_data_socket._send(self.clientsocket, data)  
        # Actualizar informacion del paralelismo del contenedor 
        if inter_parallelism > 0:
            # Actualizar informacion del inter paralelismo del contenedor
            self.intraUser_parallelism= inter_parallelism
            self.interExecution_parallelism= inter_parallelism
        if intra_parallelism >0:
            # Actualizar informacion del intra paralelismo del contenedor
            self.intraUser_parallelism= intra_parallelism
            self.intraExecution_parallelism= intra_parallelism
