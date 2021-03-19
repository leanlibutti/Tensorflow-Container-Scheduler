import abc
from abc import ABCMeta
from system import systemInfo
import queue

class SchedulingPolicy(metaclass=ABCMeta):

    def __init__(self, assigment_type, feedback=False):
        self.__assignment_type= assigment_type
        self.__feedback= feedback
        self.__queue_array=[]
        self.__queue_pending_array= []

    def get_feedback(self):
        return self.__feedback
    
    def get_assigment_type(self):
        return self.__assignment_type
    
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

class FFSnotReassignment(SchedulingPolicy):

    def __init__(self, assigment_type, feedback=False):
        super().__init__(assigment_type, feedback)
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

class FFSReassignment(SchedulingPolicy):

    def __init__(self):
        super().__init__()

    # Define la cantidad de nuevo paralelismo requerido por el contenedor
    # inter_parallelism e intra_parallelism puede ser negativos.
    def schedule_parallelism(self, resources_availables, inter_parallelism, intra_parallelism):
        # Lista que define los parámetros devueltos por la política de planificación (inter e intra paralelismo para un determinado contenedor)
        parameters_list= []
        print('Paralelismo requerido: ', inter_parallelism+intra_parallelism, ' - Paralelismo libre: ', resources_availables)
        if resources_availables >= (inter_parallelism+intra_parallelism):
            parameters_list.append(inter_parallelism)
            parameters_list.append(intra_parallelism) 
        else: 
            if resources_availables % 2:
                parameters_list.append(resources_availables/2) # inter paralelismo
                parameters_list.append(resources_availables/2) # intra paralelismo
            else: 
                parameters_list.append(resources_availables//2) # inter paralelismo
                parameters_list.append((resources_availables//2)+1) # intra paralelismo

        print('Paralelismo devuelto por politica de planificacion: ', parameters_list)
        return parameters_list