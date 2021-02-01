import os
import multiprocessing

class systemInfo:

    def __init__(self):

        self.cores= multiprocessing.cpu_count()
        self.cores_used=0

    def check_resources(self):

        return self.cores - self.cores_used

    def apply_resources(self, parallelism):

        if parallelism > (self.cores - self.cores_used):
            return False
        else:
            self.cores_used= self.cores_used + parallelism
            return True

    def free_resources(self, parallelism):
        self. cores_used= self.cores_used - parallelism