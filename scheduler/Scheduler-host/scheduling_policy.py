import abc
from abc import ABCMeta
from system import systemInfo
import queue

class SchedulingPolicy(metaclass=ABCMeta):

    def __init__(self, reassigment_type, preemptive, feedback=False):
        self.__reassignment_type= reassigment_type
        self.__feedback= feedback
        self.__preemptive= preemptive
        self.__queue_array=[]
        self.__queue_pending_array= []

    def get_feedback(self):
        return self.__feedback
    
    def get_reassigment_type(self):
        return self.__reassignment_type
    
    def get_queue_request(self, id_queue):
        if not self.__queue_array[id_queue].empty():
            return self.__queue_array[id_queue].get()
        else: 
            return []
        
    def get_pending_queue_request(self, id_queue):
        if not self.__queue_pending_array[id_queue].empty():
            return self.__queue_pending_array[id_queue].get()
        else: 
            return []
        
    def add_queue(self):
        self.__queue_array.append(queue.Queue())

    def add_pending_queue(self):
            self.__queue_pending_array.append(queue.Queue())

    def add_queue_request(self,id_queue, data):
        self.__queue_array[id_queue].put(data)
        
    def add_pending_queue_request(self,id_queue, data):
        self.__queue_pending_array[id_queue].put(data)
        
    @abc.abstractmethod
    def get_new_request(self):
        """ Definir cómo retornar una nueva peticion"""
        
    @abc.abstractmethod    
    def get_pending_request(self):
            """ Definir cómo retornar una peticion pendiente"""
    
    @abc.abstractmethod   
    def add_new_request(self):
        """ Definir cómo agregar una nueva peticion a alguna de las colas de la política de planificación"""
        
    @abc.abstractmethod   
    def add_pending_request(self):
        """ Definir cómo agregar una nueva peticion a alguna de las colas de la política de planificación"""
        
    @abc.abstractmethod
    def schedule_parallelism(self, system_info, inter_parallelism, intra_parallelism):
        """Definir el paralelismo para el contenedor dependiendo de la politica de planificación"""

class FCFS(SchedulingPolicy):

    def __init__(self, assigment_type):
        super().__init__(assigment_type, False)
        super().add_queue()
        super().add_pending_queue()
        
    def get_new_request(self):
        return super().get_queue_request(0)
        
    def get_pending_request(self):
        return super().get_pending_queue_request(0)
    
    def add_new_request(self, data):
        super().add_queue_request(0, data)
        
    def add_pending_request(self,data):
        super().add_pending_queue_request(0,data)

    # Define la cantidad de nuevo paralelismo requerido por el contenedor
    # inter_parallelism e intra_parallelism puede ser negativos.
    def schedule_parallelism(self, resources_availables, inter_parallelism, intra_parallelism):
        # Lista que define los parámetros devueltos por la política de planificación (inter e intra paralelismo para un determinado contenedor)
        parameters_list= []
        print('Paralelismo requerido: ', inter_parallelism+intra_parallelism, ' - Paralelismo libre: ', resources_availables)
        
        reassigment= super().get_reassigment_type()
        
        if (reassigment == "strict"):
            if (inter_parallelism+intra_parallelism > 0):
                if resources_availables >= (inter_parallelism+intra_parallelism):
                    parameters_list.append(inter_parallelism)
                    parameters_list.append(intra_parallelism)
            else:
                parameters_list.append(inter_parallelism)
                parameters_list.append(intra_parallelism)
                print("Free Resources")
            print('Paralelismo devuelto por politica de planificacion: ', parameters_list)
            return parameters_list
        else:
            if (reassigment == "max_prop"):
                pass
            else:
               #Is always_attend
               pass 