# Script para el manejo de señales en el contenedor

Para la atencion de señales en el contenedor, necesitamos crear un script con el siguiente código:

##entrypoint.sh##

#Manejador de señal para el cambio del paralelismo inter
change_interParallelism() {

    #Obtener el PID de la instancia TF en ejecución (nos interesa un solo PID de todos los procesos de la instancia)
    process_id= pgrep python3* | awk NR\<2 

    #Enviar señal al proceso para cambiar el inter paralelismo
    kill -10 process_id
}

#Manejador de señal para el cambio del paralelismo intra
change_intraParallelism(){

    #Obtener el PID de la instancia TF en ejecución (nos interesa un solo PID de todos los procesos de la instancia)
    process_id_list= pgrep python3* | awk NR\<2

    #Enviar señal al proceso para cambiar el intra paralelismo
    kill -12 process_id
}

#Obtener señales para ambos paralelismo y atenderlas en las funciones definidas
trap 'change_interParallelism' 10
trap 'change_intraParallelism' 12

#Mantener el contenedor vivo (ver si es necesario esto o lanzar el programa desde aca y esperar a su finalización)
while true
do
    tail -f /dev/null & wait ${!}
done

##fin de entrypoint.sh##

# Cambios en Dockerfile para el manejo de señales

Se debe modificar el dockerfile agregando la ejecución del script cuando se inicia la ejecución del mismo:

COPY entrypoint.sh /home
EXPOSE 8080
ENTRYPOINT ["/home/entrypoint.sh"]