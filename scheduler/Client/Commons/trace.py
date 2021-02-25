import csv
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# Clase encargada de definir un evento del planificador.
class TraceEvent:

    def __init__(self, event, time ,value, value2, thread=-1):
        super().__init__()
        self.event_type= event
        self.time= time
        self.value=value
        self.value2=value2
        self.thread=thread

    def get_time(self):
        return self.time
    
    def get_event_type(self):
        return self.event_type

    def get_thread(self):
        return self.thread

    def get_value(self):
        return self.value

    def get_value2(self):
        return self.value2

class TraceLog:

    def __init__(self, threads_count):
        super().__init__()
        self.events_list= []
        self.init_systemTime_seconds= time.time() #almacenar tiempo de inicio 
        self.threads_count= threads_count

    def add_thread(self):
        self.threads_count= self.threads_count+1

    # Guarda evento en la estructura de almacenamiento
    def save_event(self, event, thread_number, event_value=-1, event_value2=-1):
        
        # Crear evento
        event= TraceEvent(event, time.time()-self.init_systemTime_seconds, event_value, event_value2, thread_number)

        # Almacenar evento en la lista
        self.events_list.append(event)

    def save_CSV(self, directory, filename):

        ok=True

        file_path= directory + filename
        
        try: 
            with open(file_path, mode='w') as csv_file:
                writer_log = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for event_l in self.events_list:
                    writer_log.writerow([event_l.get_event_type(), event_l.get_time()])
        
        except:
            ok=False
        return ok

    # Visualiza hasta 100 eventos para cada hilo (si se desean más eventos por hilo debe enviarse por parámetro)
    def plot_events(self, event_per_thread=100):
        '''
        print(" Event List before start")
        for i in range(len(self.events_list)-1):
            print(self.events_list[i].get_event_type())
        '''

        data_plot=[[]]
        
        event_list_aux=[]

        #print(self.events_list)

        for i in range(self.threads_count):
            data_event=[]
            if (len(self.events_list)!=0):
                index=0
                for j in range(0, len(self.events_list)-1):
                    #print(" Event List before remove")
                    #for h in range(len(self.events_list)-1):
                        #print(self.events_list[h].get_event_type())
                    if self.events_list[index].get_thread() == i:
                        data_event.append(self.events_list[index].get_time())
                        event_list_aux.append(self.events_list[index])
                        self.events_list.remove(self.events_list[index])
                    else:
                        index= index+1
            #print("Thread:" + str(i))
            #print("Data plot:")
            #print(data_plot)

            #print("Data Event before fill to zeros:")
            #print(data_event)

            # Completar el vector de datos del hilos para que todas las filas tenga la misma dimension
            while (len(data_event) < event_per_thread):
                data_event.append(0)

            #print("Data Event after fill to zeros:")
            #print(data_event)

            data_event= [data_event]

            if i == 0:
                data_plot= data_event
            else:
                data_plot= np.concatenate((data_plot, data_event))
        self.events_list= event_list_aux

        #print("Data Plot final:")
        #print(data_plot)

        # set different colors for each set of positions
        colors = ['C{}'.format(i) for i in range(self.threads_count)]
        #print("Colors of events:")
        #print(colors)

        threads_plot=[i for i in range(self.threads_count)]
        #print("Event_plot:")
        #print(threads_plot)

        line_lengths=[1 for i in range(self.threads_count)]
        #print("Line Lengths:")
        #print(line_lengths)

        # create a horizontal plot
        plt.eventplot(data_plot, colors=colors, lineoffsets=threads_plot, linelengths=line_lengths)

        plt.title('Events Trace')
        plt.xlabel('time (s)')
        plt.ylabel('events[integer]')

        for i in range(0, len(self.events_list)):
            data_label=str(self.events_list[i].get_event_type())+"\n"+str(self.events_list[i].get_value())+"\n"+str(self.events_list[i].get_value2())
            plt.annotate(data_label,(self.events_list[i].get_time(), self.events_list[i].get_thread()))

        plt.show()