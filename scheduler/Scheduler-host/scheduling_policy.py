import abc
from abc import ABCMeta
from system import systemInfo
import queue
from request import Start, Restart, Pause, Update, Resume, Finish

class SchedulingPolicy(metaclass=ABCMeta):

    def __init__(self, reassigment_type, preemptive, feedback=False, factor_prop=1):
        self.__reassignment_type= reassigment_type
        self.__feedback= feedback
        self.__preemptive= preemptive
        self.__factor_prop=factor_prop
        self.__queue_array=[]
        self.__queue_pending_array= []

    def get_factor_prop(self):
        return self.__factor_prop

    def get_feedback(self):
        return self.__feedback

    def get_reassigment_type(self):
        return self.__reassignment_type

    def get_queue(self, index):
        return self.__queue_array[index]

    def get_pending_queue(self, index):
            return self.__queue_pending_array[index]

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

    def set_queue(self, id_queue, q_aux):
        self.__queue_array[id_queue] = q_aux

    def set_pending_queue(self, id_queue, q_aux):
            self.__queue_pending_array[id_queue] = q_aux

    def set_factor_prop(self, fp):
        self.__factor_prop=fp

    def add_queues(self, number_queues):
        for i in range(number_queues):
            self.__queue_array.append(queue.Queue())

    def add_pending_queues(self, number_queues):
        for i in range(number_queues):
            self.__queue_pending_array.append(queue.Queue())

    def add_queue_request(self,id_queue, data):
        if (len(self.__queue_array) > 1):
            self.__queue_array[id_queue].put(data)
        else:
            self.__queue_array[0].put(data)

    def add_pending_queue_request(self,id_queue, data):
        if (len(self.__queue_pending_array) > 1):
            self.__queue_pending_array[id_queue].put(data)
        else:
            self.__queue_pending_array[0].put(data)

    # Define la cantidad de nuevo paralelismo requerido por el contenedor
    # inter_parallelism e intra_parallelism puede ser negativos.
    def schedule_parallelism(self, resources_availables, inter_parallelism, intra_parallelism, max_resources_per_cont):
        # Lista que define los parámetros devueltos por la política de planificación (inter e intra paralelismo para un determinado contenedor)
        parameters_list= []
        print('Paralelismo requerido: ', inter_parallelism+intra_parallelism, ' - Paralelismo libre: ', resources_availables)

        reassigment= self.get_reassigment_type()

        if (reassigment == "strict"):
            if (inter_parallelism+intra_parallelism > 0):
                if resources_availables >= (inter_parallelism+intra_parallelism):
                    #Agregado para asignar solamente un hilo inter ya que no produce mejoras el aumento de este paralelismo por el momento
                    if inter_parallelism > 1:
                        inter_parallelism=1
                        intra_parallelism+= inter_parallelism
                    parameters_list.append(inter_parallelism)
                    parameters_list.append(intra_parallelism)
            else:
                parameters_list.append(inter_parallelism)
                parameters_list.append(intra_parallelism)
                print("Free Resources")
        else:
            if (reassigment == "max_prop"):
                # Como minimo le doy un hilo a cada paralelismo
                if (resources_availables > 2):
                    # Obtener el factor de proporcion
                    factor_prop= self.get_factor_prop()
                    # Calcular la proporcion de inter e intra paralelismo para el contenedor
                    # El round a veces asigna mas recursos que el total disponible. Por lo tanto, directamente truncar el valor flotante de la division
                    # inter_p= max_resources_per_cont if int(inter_parallelism/factor_prop) >= max_resources_per_cont else int(inter_parallelism/factor_prop)
                    inter_p = 1 # uncomment previous line and comment this if want to use factor prop in inter parallelism
                    intra_p= max_resources_per_cont if int(intra_parallelism/factor_prop) >= max_resources_per_cont else int(intra_parallelism/factor_prop)
                    print("Inter P in scheduleparallelism:", inter_p, " - Intra P in scheduleparallelism:", intra_p)
                    if(inter_p == 0) and (inter_parallelism > 0): inter_p=1
                    if(intra_p == 0): intra_p=1
                    #inter_p=1 # debido a que al aumentar el paralelismo inter no vemos mejoras lo ponemos siempre en uno. La asignacion de interparalelismo con factor prop lo comentamos por el momento.
                    if intra_p > resources_availables - inter_p:
                        intra_p = resources_availables - inter_p
                    #Agregado para asignar solamente un hilo inter ya que no produce mejoras el aumento de este paralelismo por el momento
                    if inter_p > 1:
                        intra_p+= inter_p-1
                        inter_p=1
                    while(inter_p+intra_p > resources_availables):
                        intra_p-=1
                    parameters_list.append(inter_p)
                    parameters_list.append(intra_p)
                else:
                    if(resources_availables == 2): 
                        parameters_list.append(1)
                        parameters_list.append(1)
            else:
                #Is always attend
                if (resources_availables >= 2): # cambiado a 2 para que asigne como mínimo 1 hilo inter y 1 hilo intra
                    if (inter_parallelism+intra_parallelism <= resources_availables):
                        #Agregado para asignar solamente un hilo inter ya que no produce mejoras el aumento de este paralelismo por el momento
                        if inter_parallelism > 1:
                            inter_parallelism=1
                            intra_parallelism+= inter_parallelism
                        parameters_list.append(inter_parallelism)
                        parameters_list.append(intra_parallelism)
                    else:
                        if (inter_parallelism>0) and (intra_parallelism >0):
                            # Peticion con asignacion de ambos paralelismos
                            inter_fraction= inter_parallelism/(inter_parallelism+intra_parallelism)
                            intra_fraction= intra_parallelism/(inter_parallelism+intra_parallelism)
                            inter_p= int(round(inter_fraction*resources_availables))
                            intra_p= int(round(intra_fraction*resources_availables))
                        else:
                            # Peticion de actualizacion de un solo tipo de paralelismo
                            if(inter_parallelism>0):
                                inter_p=resources_availables
                                intra_p=0
                            else:
                                inter_p=0
                                intra_p=resources_availables
                        if inter_p == 0:
                            inter_p= inter_p+1
                            intra_p= intra_p-1
                        if intra_p == 0:
                            intra_p= intra_p+1
                            inter_p= inter_p-1
                        #Agregado para asignar solamente un hilo inter ya que no produce mejoras el aumento de este paralelismo por el momento
                        if inter_p > 1:
                            inter_p=1
                            intra_p+= inter_p-1
                        parameters_list.append(inter_p)
                        parameters_list.append(intra_p)
        print('Paralelismo devuelto por politica de planificacion: ', parameters_list)
        return parameters_list

    @abc.abstractmethod
    def get_new_request(self):
        """ Definir cómo retornar una nueva peticion"""

    @abc.abstractmethod
    def get_pending_request(self):
            """ Definir cómo retornar una peticion pendiente"""

    @abc.abstractmethod
    def queue_empty(self):
        """ Debe devolver verdadero en caso de que todas las colas de nuevas peticiones estén vacías """

    @abc.abstractmethod
    def pending_queue_empty(self):
        """ Debe devolver verdadero en caso de que todas las colas de peticiones pendientes estén vacías """

    @abc.abstractmethod
    def calculate_factor_prop(self, resources_availables, execInfo_list):
        """Definir el factor de proporcion cuando se utiliza la reasignacion max_prop"""

class FCFS(SchedulingPolicy):

    def __init__(self, assigment_type):
        super().__init__(assigment_type, False)
        super().add_queues(1)
        super().add_pending_queues(1)

    def get_new_request(self):
        return super().get_queue_request(0)

    def get_pending_request(self):
        return super().get_pending_queue_request(0)

    def pending_queue_empty(self):
        if(super().get_pending_queue(0).empty()):
            return -1
        else:
            return 0

    def queue_empty(self):
        if(super().get_queue(0).empty()):
            return -1
        else:
            return 0

    def calculate_factor_prop(self, resources_availables, execInfo_list):
        total_resources=0
        q_aux= queue.Queue()
        q_pending= super().get_pending_queue(0)
        while (not q_pending.empty()):
            request_=q_pending.get()
            if isinstance(request_, Start) or isinstance(request_, Resume) or isinstance(request_, Restart):
                total_resources+= request_.get_inter_parallelism()+request_.get_intra_parallelism()
            else:
                for x in execInfo_list:
                    if x.get_request_id() == request_.get_request_id():
                        parallelism_request= request_.get_inter_parallelism()+request_.get_intra_parallelism()
                        parallelism_container= x.get_inter_exec_parallelism()+x.get_intra_exec_parallelism()
                        if(parallelism_request > parallelism_container):
                            total_resources+= parallelism_request - parallelism_container
            q_aux.put(request_)
        while not q_aux.empty():
            self.add_pending_queue_request(0,q_aux.get())
        # Recorrer la lista de peticiones pendientes (comienzo, act, resumen o pausa) y ver la cantidad total de recursos solicitados
        q_= super().get_queue(0)
        while (not q_.empty()):
            request_=q_.get()
            if isinstance(request_, Start) or isinstance(request_, Resume) or isinstance(request_, Restart):
                total_resources+= request_.get_inter_parallelism()+request_.get_intra_parallelism()
            else:
                for x in execInfo_list:
                    if x.get_request_id() == request_.get_request_id():
                        parallelism_request= request_.get_inter_parallelism()+request_.get_intra_parallelism()
                        parallelism_container= x.get_inter_exec_parallelism()+x.get_intra_exec_parallelism()
                        if(parallelism_request > parallelism_container):
                            total_resources+= parallelism_request - parallelism_container
            q_aux.put(request_)
        while not q_aux.empty():
            self.add_queue_request(0, q_aux.get())
        # Calcular factor de proporcion
        new_fp= total_resources/resources_availables
        if new_fp != 0:
            super().set_factor_prop(new_fp)
            print("New factor prop = ", new_fp)
        else:
            super().set_factor_prop(int(1))
            print("New factor prop = 1")
        if super().get_queue(0).empty():
            print("Queue is empty")

class Priority(SchedulingPolicy):

    def __init__(self, assigment_type, number_priorities):
        super().__init__(assigment_type, False)
        super().add_queues(number_priorities)
        super().add_pending_queues(number_priorities)
        self.__priorities= number_priorities

    def get_new_request(self):
        for i in range(self.__priorities):
            request= super().get_queue_request(i)
            if request:
                return request   
        return [] 

    def get_pending_request(self):
        for i in range(self.__priorities):
            request= super().get_pending_queue_request(i)
            if request:
                return request   
        return [] 

    def pending_queue_empty(self):
        for i in range(self.__priorities):
            if (not super().get_pending_queue(i).empty()):
                return i
        return -1

    def queue_empty(self):
        for i in range(self.__priorities):
            if (not super().get_queue(i).empty()):
                return i
        return -1

    def calculate_factor_prop(self, resources_availables, execInfo_list):
        total_resources=0
        n_queue_pending= self.pending_queue_empty()
        n_queue_new= self.queue_empty()
        priority=-1
        if(n_queue_new == n_queue_pending):
            priority= n_queue_new
        else:
            if(n_queue_new > n_queue_pending):
                priority= n_queue_new
            else:
                priority=  n_queue_pending
        
        if(priority != -1):
            q_aux= queue.Queue()
            request_= self.get_pending_queue_request(priority)
            while(request_):
                if isinstance(request_, Start) or isinstance(request_, Resume) or isinstance(request_, Restart):
                    total_resources+= request_.get_inter_parallelism()+request_.get_intra_parallelism()
                else:
                    for x in execInfo_list:
                        if x.get_request_id() == request_.get_request_id():
                            parallelism_request= request_.get_inter_parallelism()+request_.get_intra_parallelism()
                            parallelism_container= x.get_inter_exec_parallelism()+x.get_intra_exec_parallelism()
                            if(parallelism_request > parallelism_container):
                                total_resources+= parallelism_request - parallelism_container
                q_aux.put(request_)
                request_= self.get_pending_queue_request(priority)
            while not q_aux.empty():
                self.add_pending_queue_request(priority,q_aux.get())

            # Recorrer la lista de peticiones pendientes (comienzo, act, resumen o pausa) y ver la cantidad total de recursos solicitados
            request_= self.get_queue_request(priority)
            while (request_):
                if isinstance(request_, Start) or isinstance(request_, Resume) or isinstance(request_, Restart):
                    total_resources+= request_.get_inter_parallelism()+request_.get_intra_parallelism()
                else:
                    for x in execInfo_list:
                        if x.get_request_id() == request_.get_request_id():
                            parallelism_request= request_.get_inter_parallelism()+request_.get_intra_parallelism()
                            parallelism_container= x.get_inter_exec_parallelism()+x.get_intra_exec_parallelism()
                            if(parallelism_request > parallelism_container):
                                total_resources+= parallelism_request - parallelism_container
                q_aux.put(request_)
                request_= self.get_queue_request(priority)
            while not q_aux.empty():
                self.add_queue_request(priority, q_aux.get())
        # Calcular factor de proporcion
        new_fp= total_resources/resources_availables
        if new_fp != 0:
            self.set_factor_prop(new_fp)
            print("New factor prop = ", new_fp)
        else:
            self.set_factor_prop(int(1))
            print("New factor prop = 1")
