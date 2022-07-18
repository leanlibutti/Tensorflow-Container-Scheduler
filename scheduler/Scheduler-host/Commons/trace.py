import os
import csv
import time
import numpy as np
import plotly.express as px
import datetime
import sys
#from operator import itemgetter

log_file=False

# Clase encargada de definir un evento del planificador.
class TraceEvent:

    def __init__(self, event, time , inter_exec=-1, intra_exec=-1, container=-1, inter_user=-1, intra_user=-1):
        super().__init__()
        self.event_type= event
        self.time= time
        self.inter_user= inter_user
        self.intra_user= intra_user
        self.inter_exec= inter_exec
        self.intra_exec= intra_exec
        self.container= container

    def get_time(self):
        return self.time
    
    def get_event_type(self):
        return self.event_type

class TraceLog:

    def __init__(self, policy="", tf_version="", tf_model="", threads_count=0):
        super().__init__()
        self.__events_list= []
        self.__df_events= []
        self.__init_systemTime_seconds= time.time() #almacenar tiempo de inicio 
        self.__threads_count= threads_count
        self.__policy= policy
        self.__tf_version=tf_version
        self.__tf_model= tf_model

    def add_thread(self):
        self.__threads_count= self.__threads_count+1
        
    def set_tf_model(self, tf_model):
        self.__tf_model= tf_model
    
    def set_policy(self, policy):
        self.__policy= policy
    
    def set_tf_version(self, tf_version):
        self.__tf_version= tf_version
        
    # Guarda evento en la estructura de almacenamiento
    def save_event(self, event, request_id=-1, inter_exec=-1, intra_exec=-1, inter_user=-1, intra_user=-1, container_id=-1):
        
        if event=="start_request":
            # Crear evento
            event_=dict(Request_id=request_id, Model= self.__tf_model, Policy=self.__policy, Tensorflow=self.__tf_version, Container="null", Inter_Parallelism_Request=inter_user, Intra_Parallelism_Request=intra_user, Inter_Parallelism_Initial=-1, Intra_Parallelism_Initial=-1, Start_Request=datetime.datetime.now(), Update_Count=0, Pause_Count=0, Reassigment_Count=0)
            self.__events_list.append(event_)
            #event_= TraceEvent(event, time.time()-self.init_systemTime_seconds, inter_exec, intra_exec, container, inter_user, intra_user)
        else:
            if event=="start_attention":
                print("Entry start attention event") if log_file else None
                print("Container id recieved:", container_id, " - Request id recieved:", request_id) if log_file else None
                for container in self.__events_list:
                    if (int(container["Request_id"]) == int(request_id)):
                        print("Start attention event saved") if log_file else None
                        self.__events_list.remove(container)
                        container["Container"] = container_id
                        container["Inter_Parallelism_Initial"] = inter_exec
                        container["Intra_Parallelism_Initial"] = intra_exec
                        container["Execution_Start"] = datetime.datetime.now()
                        self.__events_list.append(container)
                        break
            else:
                if(event=="update_request"):
                    for container in self.__events_list:
                        if (int(container["Request_id"]) == int(request_id)):
                            self.__events_list.remove(container)
                            container["Update_Count"] +=1
                            name_update= "Update_Request_" + str(container["Update_Count"])
                            container[name_update] = datetime.datetime.now(
                            self.__events_list.append(container)
                            )
                            break
                else:
                    if(event=="update_attention"):
                        for container in self.__events_list:
                            if container["Container"] != "null":
                                if (int(container["Container"]) == int(container_id)):
                                    self.__events_list.remove(container)
                                    name_update= "Update_Attention_" + str(container["Update_Count"])
                                    container[name_update] = datetime.datetime.now()
                                    container[name_update+"_Inter"] = inter_exec
                                    container[name_update+"_Intra"] = intra_exec
                                    self.__events_list.append(container)
                                    break
                    else:
                        if(event=="pause_start"):
                            for container in self.__events_list:
                                if (int(container["Container"]) == int(container_id)):
                                    if container["Container"] != "null":
                                        self.__events_list.remove(container)
                                        container["Pause_Count"] +=1
                                        name_pause= "Pause_Start_" + str(container["Pause_Count"])
                                        container[name_pause] = datetime.datetime.now()
                                        self.__events_list.append(container)
                                        break
                        else:
                            if(event=="pause_finish"):
                                for container in self.__events_list:
                                    if container["Container"] != "null":
                                        if (int(container["Container"]) == int(container_id)):
                                            self.__events_list.remove(container)
                                            name_pause= "Pause_Finish_" + str(container["Pause_Count"])
                                            container[name_pause] = datetime.datetime.now()
                                            self.__events_list.append(container)
                                            break
                            else:
                                if (event=="reassigment"):
                                    for container in self.__events_list:
                                        if container["Container"] != "null":
                                            if (int(container["Container"]) == int(container_id)):
                                                self.__events_list.remove(container)
                                                container["Reassigment_Count"] +=1
                                                name_r= "Reassigment_" + str(container["Reassigment_Count"])
                                                container[name_r] = datetime.datetime.now()
                                                container[name_r+"_Inter"] = inter_exec
                                                container[name_r+"_Intra"] = intra_exec
                                                self.__events_list.append(container)
                                                break
                                else:   
                                    for container in self.__events_list:
                                        if container["Container"] != "null":
                                            if (int(container["Container"]) == int(container_id)):
                                                self.__events_list.remove(container)
                                                print("finish container event saved") if log_file else None
                                                container["Execution_Finish"] = datetime.datetime.now()
                                                self.__events_list.append(container)
                                                break

    def save_CSV(self, directory, filename="output.txt"):
        ok=True
        csv_file= directory + filename
        csv_columns= ['Model','Policy','Tensorflow', "Container", "Inter_Parallelism_Request", "Intra_Parallelism_Request", "Inter_Parallelism_Initial", "Intra_Parallelism_Initial", "Start_Request", "Execution_Start", "Execution_Finish", "Reassigment_1","Reassigment_1_Inter","Reassigment_1_Intra","Reassigment_2","Reassigment_2_Inter","Reassigment_2_Intra", "Update_Request_1", "Update_Attention_1", "Update_Attention_1_Inter", "Update_Attention_1_Intra", "Pause_Start_1", "Pause_Finish_1", "Reassigment_Count", "Pause_Count", "Update_Count","Request_id", "Execution_Time", "First_Execution_Time", "Wait_Time"]
        try: 
            with open(csv_file, mode='w') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
                writer.writeheader()
                for data in self.__events_list:
                    writer.writerow(data)
        except BaseException as e:
            print("Failed CSV save") if log_file else None
            print(e) if log_file else None
        
    
    ##### Gantt Diagram #####
    
    # Almacenar comienzo de ejecución del contenedor en dataframe        
    def init_container_event(self,container, threads, request_id):
        self.__df_events.append(dict(Task=container, Start=datetime.datetime.now(), Finish=-1, Cores=threads, RequestId= request_id))
        
    # Asignar tiempo de finalizacion del contenedor en el dataframe y generar el timeline de los steps de tensorflow
    def finish_container_event(self, container_number, time_steps):
        container_number = int(container_number)
        try: 
            start_datetime_step=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            start_datetime_step= datetime.datetime.strptime(start_datetime_step, '%Y-%m-%d %H:%M:%S')
            if time_steps:
                for container in self.__df_events:
                    if ((int(container["Task"]) == container_number) and (start_datetime_step > container["Start"])):
                        start_datetime_step= container["Start"] 
                n_container= container_number + 0.5
                colour=1
                for time_step in time_steps:
                    added_seconds= datetime.timedelta(0, int(time_step))
                    finish_datetime_step= start_datetime_step + added_seconds
                    self.__df_events.append(dict(Task=n_container, Start=start_datetime_step, Finish=finish_datetime_step, Cores=colour))
                    if colour==1:
                        colour=2
                    else:
                        colour=1
                    start_datetime_step= finish_datetime_step
            else:
                print("No time steps in container: ", str(container_number)) if log_file else None
            for container in self.__df_events:
                if ((int(container["Task"]) == container_number) and (not isinstance(container["Finish"], datetime.datetime))):
                    container["Finish"] = datetime.datetime.now()
                    print("Changes finish container: ", str(container_number)) if log_file else None
        except BaseException as e:
            print(repr(e)) if log_file else None
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno) if log_file else None
            print("Base error") if log_file else None
                
    def plot_gantt(self, day):
        fig = px.timeline(self.__df_events, x_start="Start", x_end="Finish", y="Task", color="Cores")
        fig.update_yaxes(autorange="reversed")
        time_start= day + '00:00'
        time_finish= day + '00:30'
        fig.update_xaxes(autorange= False, range=[time_start, time_finish])
        fig.show()
        
    def save_gantt(self, directory, filename="output.txt"):
        keys = self.__df_events[0].keys()
        a_file = open(directory+filename, "w")
        dict_writer = csv.DictWriter(a_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(self.__df_events)
        a_file.close()
                    
    def load_gantt(self, directory, cant_containers, filename="output.txt"):
        data = open(directory+filename, 'r')
        start_scheduler = datetime.datetime.now()+datetime.timedelta(hours=5) 
        start_scheduler = start_scheduler.strftime('%Y-%m-%d %H:%M:%S')
        start_scheduler= datetime.datetime.strptime(start_scheduler, '%Y-%m-%d %H:%M:%S')
        finish_scheduler= datetime.datetime(1980, 5, 13, 22, 50, 55) 
        for line in csv.DictReader(data):
            if (line['Task'] == '-1'):
                time_start= datetime.datetime.strptime(line['Start'][:18], '%Y-%m-%d %H:%M:%S')
                if ( time_start < start_scheduler):
                    start_scheduler= time_start
                    continue
            time_finish= datetime.datetime.strptime(line['Finish'][:18], '%Y-%m-%d %H:%M:%S')
            if (time_finish > finish_scheduler):
                finish_scheduler= time_finish
        # print(start_scheduler)
        # print(finish_scheduler)
        timedelta=0
        if (start_scheduler.day != finish_scheduler.day):
            start_scheduler+=datetime.timedelta(hours=12) 
            timedelta=12
            # print('Change timedelta')
            # print('New start scheduler: ' , start_scheduler)
        day= str(finish_scheduler.strftime('%Y-%m-%d '))
        data.close()
        data = open(directory+filename, 'r')   
        for line in csv.DictReader(data):
            time_start= datetime.datetime.strptime(line['Start'][:19], '%Y-%m-%d %H:%M:%S')+datetime.timedelta(hours=timedelta) 
            time_finish= datetime.datetime.strptime(line['Finish'][:19], '%Y-%m-%d %H:%M:%S')+datetime.timedelta(hours=timedelta) 
            time_start_delta= str (time_start - start_scheduler)
            # print(time_start)
            # print(start_scheduler)
            # print(time_start_delta)
            time_start_delta= day + time_start_delta
            time_finish_delta= str (time_finish - start_scheduler)
            time_finish_delta= day + time_finish_delta
            line['Start'] = time_start_delta
            line['Finish'] = time_finish_delta
            # print( line['Start'], ' -- ',  line['Finish'])
            self.__df_events.append(line)
        data.close()
    
        #self.__df_events = sorted(self.__df_events, key= itemgetter("Task"))

        aux=[]
        for i in range(cant_containers):
            for timeline in self.__df_events:
                if (timeline['Task'] == str(i)):
                    aux.append(timeline)
            number_timeline_epoch= i + 0.5
            for timeline in self.__df_events:
                if (timeline['Task'] == str(number_timeline_epoch)):
                    aux.append(timeline)
        self.__df_events = aux
        return day
                
    #### End Gantt Diagram #####


    ### Calculation of metrics ####

    def calculate_meantime_container(self, number_containers, directory, filename="output.txt"):
        csv_file= directory + "times_containers_" + str(len(self.__events_list)) + ".txt"
        total_seconds=0
        max_container_time=-1
        min_container_time=9999
        for number_c in range(number_containers):
            total_container=0
            data = open(directory+filename, 'r')
            for container in csv.DictReader(data):
                if (float(container["Task"]) == float(number_c)):
                    time_start= datetime.datetime.strptime(container['Start'][:19], '%Y-%m-%d %H:%M:%S')
                    time_finish= datetime.datetime.strptime(container['Finish'][:19], '%Y-%m-%d %H:%M:%S')
                    time_delta= (time_finish-time_start).total_seconds()
                    total_container= total_container + time_delta
            data.close()
            total_seconds= total_seconds + total_container
            if (total_container > max_container_time):
                max_container= number_c
                max_container_time= total_container
            if (total_container< min_container_time):
                min_container_time= total_container
        return [max_container_time, min_container_time]

    def calculate_throughput(self, number_containers, directory, data_filename, save_filename='throughput.txt'):
        data = open(directory+data_filename, 'r')
        start_scheduler = datetime.datetime.now()+datetime.timedelta(hours=5) 
        start_scheduler = start_scheduler.strftime('%Y-%m-%d %H:%M:%S')
        start_scheduler= datetime.datetime.strptime(start_scheduler, '%Y-%m-%d %H:%M:%S')
        finish_scheduler= datetime.datetime(1980, 5, 13, 22, 50, 55) 
        for line in csv.DictReader(data):
            if (line['Task'] == '-1'):
                time_start= datetime.datetime.strptime(line['Start'][:18], '%Y-%m-%d %H:%M:%S')
                if ( time_start < start_scheduler):
                    start_scheduler= time_start
                    continue
            time_finish= datetime.datetime.strptime(line['Finish'][:19], '%Y-%m-%d %H:%M:%S')
            if (not '.' in line['Task']) and (time_finish > finish_scheduler):
                finish_scheduler= time_finish
        if (start_scheduler.day != finish_scheduler.day):
                start_scheduler+= datetime.timedelta(hours=12)
                finish_scheduler+= datetime.timedelta(hours=12) 
        # print('Init Scheduler: ', start_scheduler)
        # print('Finish Scheduler: ', finish_scheduler)
        # print('Total time of Scheduler: ', (finish_scheduler-start_scheduler).total_seconds() )
        throughput= number_containers/((finish_scheduler-start_scheduler).total_seconds()/3600)
        # print('Throughput: ', throughput)
        with open(directory+save_filename, mode='w') as f:
            f.write(str(throughput)) 
        return [throughput ,(finish_scheduler-start_scheduler).total_seconds()]

    def calculate_responseMeantime_metric(self, directory, cant_containers, filename="output.txt"):
        data = open(directory+filename, 'r')
        events=[]
        #events_finish=[]
        for line in csv.DictReader(data):
            found= False
            time_start= datetime.datetime.strptime(line['Start'][:19], '%Y-%m-%d %H:%M:%S')
            time_finish= datetime.datetime.strptime(line['Finish'][:19], '%Y-%m-%d %H:%M:%S')
            if(line['Task'] == '-1'):
                events.append(dict(Container=line['RequestId'], TimeRecieve= time_finish, TimeStart=-1, TimeFinish=-1))
                found= True
            else:
                if(line['Task'] == '-3'):
                    events.append(dict(Container=line['Cores'], TimeRecieve= time_finish, TimeStart=-1, TimeFinish=-1))
                    found= True
                else:
                    for data_container in events:
                        if (str(data_container['Container']) == line['Task']):
                            if(data_container['TimeStart'] == -1):
                                data_container['TimeStart']= time_start
                                data_container['TimeFinish']=time_finish
                                found= True
                                #events_finish.append(data_container)
                            else:
                                pass #same container but other request
            if ((not found) and ( not '.5' in str(line['Task'])) and (line['Task'] != '-2')) : # container with change of parallelism
                 events.append(dict(Container=line['Task'], TimeRecieve= time_start, TimeStart=time_start, TimeFinish=time_finish))
        data.close()
        response_time=0
        return_time=0
        execution_time=0
        for container in events:
            # print("Container = ", container["Container"], " Recieve= ", container["TimeRecieve"], " Start= ", container["TimeStart"], " Finish= ", container["TimeFinish"])
            response_time+= (container["TimeStart"] -  container["TimeRecieve"]).total_seconds()
            return_time+=  (container["TimeFinish"] - container["TimeRecieve"]).total_seconds()
            execution_time+= (container["TimeFinish"] - container["TimeStart"]).total_seconds()
    
        # print('Meantime execution: ', execution_time/cant_containers) 
        # print('Meantime response: ', response_time/cant_containers)
        # print('Meantime real execution: ', return_time/cant_containers)
        return [execution_time/cant_containers, response_time/cant_containers, return_time/cant_containers]

    def calculate_percentage_cores_used(self, directory, filename="output.txt"):
        count_lines=0
        percent_used_accum=0
        with open(directory+filename, 'r') as f:
            for line in f:
                percent_used_accum+= float(line.split(',')[3])
                count_lines+=1
        return percent_used_accum/count_lines

# Programa Principal #
if __name__ == "__main__":
    
    if len(sys.argv) != 4:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 3") 
            raise NameError('Invalid amount of arguments')

    directory= sys.argv[1]
    filename= sys.argv[2]
    cant_containers= int(sys.argv[3])
    
    trace= TraceLog()
    day= trace.load_gantt(directory, cant_containers, filename)
    # max_min_times= trace.calculate_meantime_container(cant_containers, directory, filename)
    times= trace.calculate_responseMeantime_metric(directory, cant_containers, filename)
    data_t= trace.calculate_throughput(cant_containers, directory, filename)
    percent_cores= trace.calculate_percentage_cores_used(directory, 'occupation_timeline.csv')
    trace.plot_gantt(day)
    print (times[0], ',', times[1], ',', times[2], ',', percent_cores, ',' , data_t[0], ',', data_t[1])