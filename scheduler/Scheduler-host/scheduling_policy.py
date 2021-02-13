import abc
from abc import ABCMeta
from system import systemInfo

class SchedulingPolicy(metaclass=ABCMeta):

    def __init__(self):
        pass

    @abc.abstractmethod
    def schedule_parallelism(self, system_info, inter_parallelism, intra_parallelism):
        """Definir el paralelismo para el contenedor dependiendo de la politica de planificación y 
        de los recursos disponibles"""


class FFSnotReassignment(SchedulingPolicy):

    def __init__(self):
        super().__init__()

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