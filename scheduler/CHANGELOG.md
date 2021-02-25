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