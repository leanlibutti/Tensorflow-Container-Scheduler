from datetime import datetime
import time

t = time.localtime()
current_time = time.strftime("%H:%M:¿%S", t)
print(current_time)

millis = int(round(time.time()))
print (time.time())


now = datetime.now()

current_time = now.strftime("%H:%M:%S")
print("Current Time =", current_time)
