# Clase que contiene la información asociada a una instancia de ejecución de Tensorflow
class ExecutionInfo:
    def __init__(self, container_name, container_port, docker_ps, interUser_parallelism, intraUser_parallelism, interExecution_parallelism, intraExecution_parallelism, clientsocket):
        self.container_name = container_name
        self.docker_ps = docker_ps
        self.interUser_parallelism = interUser_parallelism
        self.intraUser_parallelism = intraUser_parallelism
        self.intraExecution_parallelism = intraExecution_parallelism
        self.interExecution_parallelism = interExecution_parallelism
        self.container_port = container_port
        self.clientsocket = clientsocket

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

    # Actualizar el paralelismo total del contenedor en ejecución
    # Retorna si la operacion de actualización se pudo realizar correctamente
    def updateParallelism(self, inter_parallelism=0, intra_parallelism=0):
        # Nuevo paralelismo total soportado por el contenedor
        new_parallelism= inter_parallelism + intra_parallelism

        # Comando de actualización del paralelismo del contenedor
        run_command= 'docker update ' + str(self.docker_ps) + ' --cpus ' + str(new_parallelism)        
        
        if inter_parallelism > 0:
            # Setear las variable de entorno correspondiente al paralelismo inter de la instancia de Tensorflow actual (hacer en el cliente del contenedor)
            #os.environ["INTER_PARALELLISM"] = inter_parallelism
            #kill_command= "docker kill --signal=10 " + docker_ps # verificar si es esa señal (numero) 
            self.clientsocket.send(bytes(str(10), 'utf-8'))
            self.clientsocket.send(bytes(str(inter_parallelism), 'utf-8'))
       
            # Enviar señal que sera capturada por la instancia de Tensorflow dentro del contenedor
            #process_command = Popen([kill_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            #stdout, stderr = process_command.communicate()

            # Actualizar informacion del inter paralelismo del contenedor
            self.intraUser_parallelism= inter_parallelism
            self.interExecution_parallelism= inter_parallelism

            '''
            if (len(stderr)):
                print(stderr)
                return False
            '''

        if intra_parallelism >0:
            # Setear las variable de entorno correspondiente al paralelismo inter de la instancia de Tensorflow actual (hacer en el cliente del contenedor)
            #os.environ["INTRA_PARALELLISM"]  = intra_parallelism 
            #kill_command= "docker kill --signal=12 " + docker_ps # verificar si es esa señal (numero)
            self.clientsocket.send(bytes(str(12), 'utf-8'))
            self.clientsocket.send(bytes(str(intra_parallelism), 'utf-8'))
            
            # Enviar señal que sera capturada por la instancia de Tensorflow dentro del contenedor
            #process_command = Popen([kill_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            #stdout, stderr = process_command.communicate()

            # Actualizar informacion del intra paralelismo del contenedor
            self.intraUser_parallelism= intra_parallelism
            self.intraExecution_parallelism= intra_parallelism

            '''
            if (len(stderr)):
                print(stderr)
                return False
            '''

        # Actualizar paralelismo del contenedor
        #process_command = Popen([run_command], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
        #stdout, stderr = process_command.communicate()

        '''
        if (len(stderr)):
            print(stderr)
            return False
        else:
            print("Updated parallelism for container: ", self.container_name, " - Inter Parallelism: ", inter_parallelism, " Intra Parallelism: ", intra_parallelism)
            return True
        '''
