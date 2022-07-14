class Request():
    def __init__(self, request_id, inter_parallelism=-1, intra_parallelism=-1, priority=0):
        self.__request_id=request_id
        self.__inter_parallelism=inter_parallelism
        self.__intra_parallelism=intra_parallelism
        self.__priority = priority
        
    def get_request_id(self):
        return  self.__request_id
    
    def get_inter_parallelism(self):
        return self.__inter_parallelism
    
    def get_intra_parallelism(self):
        return self.__intra_parallelism

    def get_priority(self):
        return self.__priority

class Start(Request):
    def __init__(self, request_id, image, inter_parallelism, intra_parallelism, priority):
        super().__init__( request_id,inter_parallelism, intra_parallelism, priority)
        self.__image= image

    def get_image(self):
        return self.__image

class Update(Request):
    def __init__(self, request_id, inter_parallelism=-1, intra_parallelism=-1, priority=0):
        super().__init__(request_id,inter_parallelism, intra_parallelism, priority)

class Restart(Request):
    def __init__(self, request_id, container_name, inter_parallelism, intra_parallelism, image, priority):
        super().__init__(request_id, inter_parallelism, intra_parallelism, priority)
        self.container_name= container_name
        self.__image= image

    def get_container_name(self):
        return self.container_name
    
    def get_image(self):
        return self.__image
    
class Finish(Request):
     def __init__(self, request_id):
         super().__init__(request_id)
         
class Resume(Request):
     def __init__(self, request_id):
         super().__init__(request_id)
         
class Pause(Request):
     def __init__(self, request_id):
         super().__init__(request_id)