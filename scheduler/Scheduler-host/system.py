import os
import multiprocessing
import psutil

class systemInfo:

    def __init__(self):
        self.cores= multiprocessing.cpu_count()
        self.cores_used=0

    def total_cores(self):
        return self.cores
    
    def check_resources(self):
        return self.cores - self.cores_used

    def apply_resources(self, parallelism, not_control=False):
        if ((not not_control) and (parallelism > (self.cores - self.cores_used))):
            return False
        else:
            self.cores_used= self.cores_used + parallelism
            return True

    def free_resources(self, parallelism):
        self. cores_used= self.cores_used - parallelism

    def system_occupation(self):
        return (self.cores_used/self.cores)*100

    def memory_usage(self):
        return psutil.virtual_memory()[2]