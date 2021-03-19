from Commons import json_data_socket
from subprocess import Popen, PIPE, STDOUT
import threading

# Clase que contiene la información asociada a una instancia de ejecución de Tensorflow
class ExecutionInfo:
    def __init__(self, container_name, container_number, container_port, docker_ps, inter_user_parallelism, intra_user_parallelism, inter_exec_parallelism, intra_exec_parallelism, clientsocket):
        self.container_name = container_name
        self.docker_ps = docker_ps
        self.inter_user_parallelism = inter_user_parallelism
        self.inter_exec_parallelism = inter_exec_parallelism
        self.intra_user_parallelism = intra_user_parallelism
        self.intra_exec_parallelism = intra_exec_parallelism
        self.container_port = container_port
        self.clientsocket = clientsocket
        self.container_number=container_number
        self.lock_state= threading.Lock()
        self.state= "start"
        self.cv= threading.Condition()

    def get_inter_user_parallelism(self):
        return self.inter_user_parallelism
    
    def get_intra_user_parallelism(self):
        return self.intra_user_parallelism

    def get_inter_exec_parallelism(self):
        return self.inter_exec_parallelism
        
    def get_intra_exec_parallelism(self):
        return self.intra_exec_parallelism
    
    def get_state(self):
        self.lock_state.acquire()
        state= self.state
        self.lock_state.release()
        return state
    
    def set_state(self, new_state):
        self.lock_state.acquire()
        self.state= new_state
        self.lock_state.release()
        
    def set_inter_user_parallelism(self, new_inter_user_parallelism):
        self.inter_user_parallelism = new_inter_user_parallelism

    def set_intra_user_parallelism(self, new_intra_user_parallelism):
        self.intra_user_parallelism = new_intra_user_parallelism

    def set_inter_exec_parallelism(self, new_interExec_parallelism):
        self.inter_exec_parallelism = new_interExec_parallelism
    
    def set_intra_exec_parallelism(self, new_intraExec_parallelism):
        self.intra_exec_parallelism = new_intraExec_parallelism

    # Retorna el nombre del contenedor de la instancia TF en ejecución
    def get_container_name(self):
        return self.container_name

    def getContainerNumber(self):
        return self.container_number

    # Actualizar el paralelismo total del contenedor en ejecución
    # Retorna si la operacion de actualización se pudo realizar correctamente
    def update_parallelism(self, inter_parallelism=0, intra_parallelism=0):
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
            self.inter_user_parallelism= inter_parallelism
            self.inter_exec_parallelism= inter_parallelism
        if intra_parallelism >0:
            # Actualizar informacion del intra paralelismo del contenedor
            self.intra_user_parallelism= intra_parallelism
            self.intra_exec_parallelism= intra_parallelism
    
    def pause_container(self):
        run_command= 'docker pause ' + str(self.container_name) 
        pause_container = Popen(run_command, shell=True)
        self.state= "pause"
        
    def resume_container(self):
        run_command= 'docker unpause ' + str(self.container_name) 
        resume_container = Popen(run_command, shell=True)
        self.state= "start"
        
    def wait_execution(self):
        with self.cv:
            print("Wait in CV container...")
            self.cv.wait()
    
    def signal_execution(self):
        with self.cv:
            print("Signal in CV container...")
            self.cv.notify()
