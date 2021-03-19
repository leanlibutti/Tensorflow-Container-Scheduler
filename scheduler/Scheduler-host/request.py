class Request():
    def __init__(self, container_name, inter_parallelism=-1, intra_parallelism=-1):
        self.__container_name= container_name
        self.__inter_parallelism= inter_parallelism
        self.__intra_parallelism= intra_parallelism
        
    def get_container_name(self):
        return  self.__container_name   
    
    def get_inter_parallelism(self):
        return self.__inter_parallelism
    
    def get_intra_parallelism(self):
        return self.__intra_parallelism

class Start(Request):
    def __init__(self, container_name, image, inter_parallelism, intra_parallelism):
        super().__init__(container_name,inter_parallelism, intra_parallelism)
        self.__image= image

    def get_image(self):
        return self.__image
    
class Update(Request):
    def __init__(self, container_name, inter_parallelism=-1, intra_parallelism=-1):
        super().__init__(container_name,inter_parallelism, intra_parallelism)
    
class Finish(Request):
     def __init__(self, container_name):
         super().__init__(container_name)
         
class Resume(Request):
     def __init__(self, container_name):
         super().__init__(container_name)
         
class Pause(Request):
     def __init__(self, container_name):
         super().__init__(container_name)