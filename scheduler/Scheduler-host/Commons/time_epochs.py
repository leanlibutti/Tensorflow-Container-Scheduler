import sys
import os

class TimeEpochs:
    def __init__(self):
        super().__init__()
        self.__time_per_epoch= []

    def process_TF_file(self, file_tf):
        with open(file_tf) as f:
            #print("Read line")
            line = f.readline()
            while line:
                #Process line
                #print("Process line")
                data= line.split(" - ")
                if (data):
                    split_epoch_number= data[0].split("/")
                    if(len(split_epoch_number) > 1):
                        #print("Split lenght:", len(split_epoch_number))
                        try:
                            number_step= int(split_epoch_number[0])
                            total_steps= int(split_epoch_number[1].split(" ")[0])
                            if number_step == total_steps:
                                time_epoch= data[1].split(" ")[0]
                                time_epoch= int(time_epoch.replace('s', ''))
                                #print("time epoch:", time_epoch)
                                self.__time_per_epoch.append(time_epoch)
                        except BaseException as e:
                            #print(repr(e))
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            #print(exc_type, fname, exc_tb.tb_lineno)
                            #print("Base error")
                            #print('Line epoch: ' ,split_epoch_number[0], ' - ', split_epoch_number[1])
                        except (SyntaxError, IndentationError, NameError) as err:
                            print(err)
                        except:
                            print("Unexpected error :(")
                #print("Read line")
                line = f.readline()
        return self.__time_per_epoch

# Programa Principal #
if __name__ == "__main__":
    
    if len(sys.argv) != 2:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 1")
            raise NameError('Invalid amount of arguments')

    filename= sys.argv[1]
    time_epochs= TimeEpochs()
    times= time_epochs.process_TF_file(filename)
    i=0
    for time_epoch in times:
        print('Step ', i, ': ', time_epoch)
        i+=1

