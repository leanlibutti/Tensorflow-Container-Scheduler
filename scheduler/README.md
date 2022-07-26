## Scheduler for Tensorflow Programs

Allows planning the executions of different Tensorflow programs. The user must indicate the inter and intra parallelism for each program. The planner is in charge of deciding when the execution takes place depending on the available resources and the chosen planning policy.

Docker is used for the execution of each Tensorflow program.

The whole project is developed in the python language.

## Guide

# Políticas de planificación, asignacion y reasignación (a nivel de cores)

|   | Planificación  | Asignación de recursos          | Reasignación de recursos        | Preemptive[1] | Otros[2]       |
|---|--------------- |---------------------------------|---------------------------------|---------------|----------------|
| 1 | FCFS           | STRICT, MAX_PROP, ALWAYS_ATTEND | STRICT, MAX_PROP, ALWAYS_ATTEND |     No        |        -       |
| 2 | Priority       |                                 |                                 |    Yes/No     | Realimentación |
| 3 | Round Robin [3]|                                 |                                 |     Yes       |        -       |

[1] en fase de desarrollo.
[2] y [3] no implementadas por el momento. 

1. Planificación

    * FCFS: *First Come First Served*.
    * PRIO: *Priority*.
    * Round Robin: *Round robin* con cuanto de tiempo especificado.

2. Asignación de recursos

    * STRICT: Recursos asignados estrictamente. Si no hay recursos suficientes, no se planifica y se espera en cola hasta ser planificado.
    * MAX_PROP: Maximizar recursos para adaptar a recursos disponibles. Reparto entre peticiones proporcional a recursos solicitados. 
    * ALWAYS_ATTEND: Siempre se atienden las peticiones si hay, al menos, un core disponible. 

3. Reasignación de recursos
    En todas las politicas se atienden por antiguedad del contenedor, excepto en la version priority que solo se tienen en cuenta los contenedores con mayor prioridad
    * STRICT: Se intenta reasignar la cantidad total de recursos asignados estrictamente.
    * ALWAYS_ATTEND: Siempre se intentará reasignar los recursos de los contenedores, si al menos hay un core disponible
    * MAX_PROP: Maximizar recursos para adaptar a recursos disponibles. Reparto entre contenedores proporcional a recursos solicitados.

4. *Preemption* (expropiación)

    * Preemption implementada en forma de *pause/unpause* sobre un contenedor. Si llega una petición más prioritaria, se "expulsa" (pausa) un container. 
    * Selección de candidato/s a ser pausados:
        * Mayor tiempo de ejecución acumulado.
        * Menor solicitud de recursos inicial.

5. Otros:

    * Realimentación: modificación de prioridad en tiempo real (e.g. en función de tiempo de espera).

# Cargas de trabajo

* Características de los trabajos:

    1. Tiempo de llegada
    2. Duración de las tareas
    3. Recursos solicitados
    4. Tipo de trabajo (modelo Tensorflow a lanzar).

* Paralelización de modelos

    1. Elegir 2/3 modelos y evaluar rendimiento en función de grado de paralelismo inter- e intra- (reportar tiempos de ejecución para distinto número de cores).

# Installation

The following libraries must be installed using the pip package manager:

    * python 
    * numpy
    * psutil
    * json
    * matplotlib
    * plotly

Also, install docker following the instructions in the following link: https://docs.docker.com/engine/install/ubuntu/

# Run the scheduler

Hay dos archivos que debes modificar para hacer las pruebas:

- /scheduler/Scheduler-host/requests_file.txt: se deben colocar las peticiones atendidas por el planificador. Cuando quieres ejecutar un contenedor sin cambios de paralelismo debes colocar:
       -- execution,0,tf_scheduler,12,60
               --- si usas solo esta petición quiere decir que se va a ejecutar con 12 hilos totales (1 inter y 11
                   intra). El ultimo valor indica el tiempo de espera para atender la próxima petición. En este caso no
                   tiene efecto.
       -- execution,0,tf_scheduler,2,60
          update,0,tf_scheduler,12,90
               --- Con este esquema, luego de atender la primer petición con 1 hilo inter e intra se esperan 60 segundos
                   y se atiende la segunda que es una actualización del contenedor creado anteriormente. Esta
                   actualización del paralelismo es a 12 hilos (1 inter y 11 intra).

- /scheduler/Scheduler-host/parameters.json: aquí hay varios parámetros que pueden modificarse pero los importantes son el que define la versión de tf (admite valores "maleable" u "original") y el que se llama "get_requests" para indicar de donde se obtienen las peticiones (admite valores "create" y "file" pero debes usar este último porque las definís en el archivo requests_file.txt).

Luego de hacer los cambios en esos dos archivos, el planificador se ejecuta en la carpeta /scheduler con el comando:

- sudo python3.8 run_scheduler_one.py -n name_test -p policy -ap assigment_policy -c containers -tf tf_version

Al finalizar la ejecución del planificador, se genera una carpeta en /Data/log con el nombre "name_test". Dentro de la misma se encuentra la carpeta de la prueba con el nombre {Contenedores}Contenedores_{TFversion}. Dentro de esa carpeta podes ver el timeline del algoritmo TF en la carpeta "Outputs" y otros archivos que muestran métricas o eventos del planificador.

# Métricas a reportar

* Metricas de contenedores:
    - Tiempo medio de espera (en versiones preemptive).
    - Tiempo medio total de ejecución.
    - Tiempo medio de servicio.
    - Tiempo medio hasta primera ejecución o tiempo de respuesta.

* Metricas del planificador:
    - Productividad [Contenedores/Hora].
    - Porcentaje medio de recursos utilizados 

Para obtener las metricas en formato CSV se debe lanzar el siguiente comando:

* python3 run_trace.py nombre_prueba

Donde nombre_prueba es el directorio donde se encuentran las pruebas realizadas para evaluar el comportamiento del planificador con un distribucion de tiempo de llegada y recursos solicitados.