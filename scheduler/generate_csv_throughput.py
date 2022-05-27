import sys
# Generar un csv con la productividad de un conjunto de pruebas para una determinada politica de planificacion
def main():
    try:
        if len(sys.argv) != 2:
            print("Invalid amount of arguments - Recieved: ", str(len(sys.argv)-1), " - Required: 1")
            raise NameError('Ingresar la cantidad de iteraciones')
        
        iterations= int(sys.argv[1])

        for politics in ['Strict', 'Always', 'Not_Control']:
            if politics != 'Not_Control':
                for j in ['original', 'maleable']:
                    containers=1
                    file_througput= 'Data/log/'+'throughput_' + politics + '_' + j + '.csv'
                    print(file_througput)
                    for i in range(iterations):
                        archive= 'Data/log/' + politics + '/' + j + '/' + str(containers) + 'Contenedores/throughput_' + str(containers) + '.txt' 
                        print(archive) 
                        with open(archive, 'r') as f:
                            with open(file_througput, 'a+') as t_file:
                                t_file.write(f.read())
                                t_file.write(';')
                        containers*=2
            else:
                containers=1
                file_througput= 'Data/log/'+'throughput_' + politics + '_' + j + '.csv'
                print(file_througput)
                for i in range(iterations):
                    archive= 'Data/log/' + politics + '/'  + str(containers) + 'Contenedores/throughput_' + str(containers) + '.txt' 
                    print(archive) 
                    with open(archive, 'r') as f:
                        with open(file_througput, 'a+') as t_file:
                            t_file.write(f.read())
                            t_file.write(';')
                    containers*=2

    except BaseException as e:
        print(repr(e))
        print("Base error")
    except (SyntaxError, IndentationError, NameError) as err:
        print(err)
    except socket_schedule.error as err:
        print(err)
        print("Error in socket")
    except:
        print("Unexpected error :(")

if __name__ == "__main__":
    main()