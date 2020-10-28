import signal
import time, os

def callme(num, frame):
    pass

# register the callback:
signal.signal(10, callme)

print("py: Hi, I'm %d, talk to me with 'kill -SIGUSR1 %d'"
      % (os.getpid(),os.getpid()))

# wait for signal info:
while True:
    siginfo = signal.sigwaitinfo({10})
    print("py: got %d from %d by user %d\n" % (siginfo.si_signo,
                                             siginfo.si_pid,
                                             siginfo.si_uid))