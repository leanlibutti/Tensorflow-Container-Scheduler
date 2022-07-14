# Release 1.1.0-1 (2022-07-14)

- Add Conv Net library for execute Tensorflow-Keras models
- Add scripts for testing

# Release 1.1.0 (2022-07-14)

- Add priority policy
- Fixed bugs in attention of pending requests
- Structural changes in attention requests
- Add new json paramater:
    + assigment policy (strict, always_attend, max_prop)   
- TraceLog class:
    + Change stadistic format output (CSV)
    + Delete prints 
- Add analitycs script (run_trace.py)
- Change run script for support priority policy

# Release 1.0.0 (2022-06-24)

- Stable version of scheduler with the following policies:
    + FCFS strict
    + FCFS always_attend
    + FCFS max_prop
- Add run script for scheduler (run_scheduler.py)

## Release 0.6.2 (2021-04-28)

- Added reassignment types "max_prop" and "always_attend" to FCFS policy.

## Release 0.6.1 (2021-03-26)

- Added thread that reads request file.
- Add requests file.
- The arrival of requests are visualized in the Gantt chart.
- Structural changes to scheduling_policy.

## Release 0.6.0 (2021-03-19)

- Added Request class.
- Code modularization in scheduler.
- Added docker pause handling.
- Added active container handling when you want to finish the scheduler.
- Add new event (PAUSE_CONTAINER and RESUME_CONTAINER).
- Fixed problem in gantt chart plotting.
- Add plotly and pandas libraries.
- Request queues now belong to the scheduling policy.

## Release 0.5.5 (2021-03-01)

- Add support for Gantt Charts.

- Scheduler host:
    + Changes in update function to return parallelism applied to container
    + Add event logs for Gantt chart.
    + Fixed issue in the choice of container to generate an update request.
    + Fixed issue in docker container prune which was running on every message wait.

## Release 0.5.4 (2021-02-26)

- Add event values in CSV file.

## Release 0.5.3 (2021-02-25)

- Remove finished container with command "docker container prune -f"

- Fix problems in event logs.

## Release 0.5.2 (2021-02-24)

- Attribute error in client: the signal variable had the same name as the signal class.

- Add JSON objects messages over socket.

- Trace plotting problem:
    + Add the call to add_thread in the creation of the main threads. 
    + Fixed problem in the amount of thread plots. 

## Release 0.5.1 (2021-02-22)

- Sorting the folders
    + Add Commons flder. Includes log files for the entire project.
    + Change name of dockerfile.

- Change dockerfile to indicate how the tensorflow program should be entered.o

- Scheduler
    + Correction in the generation of events.

- Client:
    + Correction in the generation of events.
    + Add number of thread parameter in signal handler.
    + Correction socket messages.

- Trace:
    + Add the registration of a new thread to save its execution traces. 
    + Add second value in trace event.
    + Thread index correction. 

## Release 0.5.0 (2021-02-18)

- The scheduler correctly responds to the execution and update requests.

- Scheduler:
    + Add keyboard input for the completion of the program.
    + Add the joins of the client threads.
    + Changes in waiting times to generate the next execution or update request.
    + Fix storing scheduler events.
    + Code ordering.

- Client:
    + The reception of messages from the scheduler was centralized in a single thread.
    + Changes in the handling of global variables. 

- Trace:
    + You can indicate the number of events drawn in the plot_events function.

## Release 0.4.1 (2021-02-16)

- Add events class. Stores the events that can be saved in the execution traces.

- Execution info:
    + Add the attribute container number.

## Release 0.4.0 (2021-02-13)

- Scheduler:
    + Error was resolved in evaluated condition (Attention thread).
    + Add evaluation of the status of the current request when old requests are served.
    + Modification of the place where the host port is increased for the next execution request.

## Release 0.3.0 (2021-02-13)

- Scheduler:
    + Changes in update request processing. Receives available resources and should not query the system.
    + Add error handling in the search for the container you want to change (Update Request thread).
    + Changes in the generation of execution requests (Execution Request thread).
    + Changes in the reception of client data.
    + Changes in the function that reallocates resources in actives containers.
    + Changes in attention of execution/update requests (Attention thread).

- Client:
    + Changes in the signal handler of the Tensorflow program. Advises the client to finish
    + Change in the attention of update requests. Condition when parallelism update runs.
    + Changes in the reception of data through the socket. Now a single data is received and not an array of 1024.
    + Add error handling in main program.

- Execution info:
    + Changes in parallelism update.

- Scheduling policy:
    + Changes in parallelism schedule for policies FFSnotReassigment and FFSwithReassigment.

## Release 0.2.0 (2021-02-03)

- Scheduler:
    + Changes in update request processing. 
    + Change in the creation of execution requests.
    + Changes in the attention of execution/update requests.
    + Changes to screen printed texts.

- Client:
    + Add logging library to store tracking information in a text file.
    + Correction of errors in the generation of strings.

- Trace:
    + The function to store the traces in CSV format now receives the directory by parameter.

- System Info:
    + Add information about total number of cores in the machine/server.

## Release 0.1.0 (2021-02-01)

- Add client executed in the container that allows to control the execution of the Tensorflow program.
- Add scheduler. Recieves requests for execution and update of tensoroflow programs. The requests have the following data:
    *type of request
    *container name
    *docker image
    *inter parallelism
    *intra parallelism 
- Add trace class. Allows you to store events from the scheduler or client, plot the events in a graph and store them in a file with CSV format.
- Add system class. Stores the information on the amount of resources available in the machine. 
- Add scheduling policy class. Defines the planning policies of the execution and update requests.
- Add execution info class. Define information of an active container.

## Release 0.0.0 (2020-10-28)

- Project creation.