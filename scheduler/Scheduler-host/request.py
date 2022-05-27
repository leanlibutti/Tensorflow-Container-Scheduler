class Request():
    def __init__(self, request_id, inter_parallelism=-1, intra_parallelism=-1):
        self.__request_id=request_id
        self.__inter_parallelism=inter_parallelism
        self.__intra_parallelism=intra_parallelism
        
    def get_request_id(self):
        return  self.__request_id
    
    def get_inter_parallelism(self):
        return self.__inter_parallelism
    
    def get_intra_parallelism(self):
        return self.__intra_parallelism

class Start(Request):
    def __init__(self, request_id, image, inter_parallelism, intra_parallelism):
        super().__init__( request_id,inter_parallelism, intra_parallelism)
        self.__image= image

    def get_image(self):
        return self.__image

class Update(Request):
    def __init__(self, request_id, inter_parallelism=-1, intra_parallelism=-1):
        super().__init__(request_id,inter_parallelism, intra_parallelism)

class Restart(Request):
    def __init__(self, request_id, container_name, inter_parallelism, intra_parallelism, image):
        super().__init__(request_id, inter_parallelism, intra_parallelism)
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