## Scheduler for Tensorflow Programs

Allows planning the executions of different Tensorflow programs. The user must indicate the inter and intra parallelism for each program. The planner is in charge of deciding when the execution takes place depending on the available resources and the chosen planning policy.

Docker is used for the execution of each Tensorflow program.

The whole project is developed in the python language.

## Guide

coming soon...

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


