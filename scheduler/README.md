## Scheduler for Tensorflow Programs

Allows planning the executions of different Tensorflow programs. The user must indicate the inter and intra parallelism for each program. The planner is in charge of deciding when the execution takes place depending on the available resources and the chosen planning policy.

Docker is used for the execution of each Tensorflow program.

The whole project is developed in the python language.

## Guide

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

- sudo python3.8 run_scheduler.py 1 1

El primer parámetro indica la cantidad de veces que quiero ejecutar el planificador y el segundo la cantidad de contenedores que se van a crear en cada ejecución del mismo.

Al finalizar la ejecución del planificador, se genera una carpeta en /Data/log con el nombre correspondiente a la cantidad de contenedores que se ejecutaron. Por ejemplo, si ejecutas un solo contenedor la carpeta se llama "1Contenedores". Dentro de esa carpeta podes ver el timeline del algoritmo TF en la carpeta "Outputs" y otros archivos que muestran métricas o eventos del planificador.

# Políticas de planificación y reasignación (a nivel de cores)

|   | Planificación | Reasignación de recursos | Preemptive | Otros |
|---|---------------|--------------------------|------------|-------|
| 1 | FCFS          | STRICT, MAX_PROP, ALWAYS_ATTEND |    No      | - |
| 2 | Priority      | STRICT, MAX_PROP, ALWAYS_ATTEND |    Yes/No  | Realimentación |
| 3 | Round Robin   | STRICT, MAX_PROP, ALWAYS_ATTEND |    Yes     | - |

1. Planificación

    * FCFS: *First Come First Served*.
    * PRIO: *Priority*.
    * Round Robin: *Round robin* con cuanto de tiempo especificado.

2. Reasignación de recursos

    * STRICT: Recursos asignados estrictamente. Si no hay recursos suficientes, no se planifica y se espera en cola hasta ser planificado.
    * MAX_PROP: Maximizar recursos para adaptar a recursos disponibles. Reparto entre contenedores proporcional a recursos solicitados. 
    * ALWAYS_ATTEND: Siempre se atienden las peticiones si hay, al menos, un core disponible. 

3. *Preemption* (expropiación)

    * Preemption implementada en forma de *pause/unpause* sobre un contenedor. Si llega una petición más prioritaria, se "expulsa" (pausa) un container. 
    * Selección de candidato/s a ser pausados:
        * Mayor tiempo de ejecución acumulado.
        * Menor solicitud de recursos inicial.

4. Otros:

    * Realimentación: modificación de prioridad en tiempo real (e.g. en función de tiempo de espera).

# Cargas de trabajo

* Características de los trabajos:

    1. Tiempo de llegada
    2. Duración de las tareas
    3. Recursos solicitados
    4. Tipo de trabajo (modelo Tensorflow a lanzar).

* Paralelización de modelos

    1. Elegir 2/3 modelos y evaluar rendimiento en función de grado de paralelismo inter- e intra- (reportar tiempos de ejecución para distinto número de cores).

# Métricas a reportar

* Para cada container:
    - Tiempo de espera (en versiones preemptive).
    - Tiempo total de ejecución.
    - Tiempo de servicio.
    - Tiempo hasta primera ejecución.

* Para cada ejecución completa:
    - Productividad (containers finalizados por segundo).