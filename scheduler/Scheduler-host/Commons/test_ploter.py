'''
import matplotlib.pyplot as plt
from matplotlib.dates import (YEARLY, DateFormatter,
                              rrulewrapper, RRuleLocator, drange)
import datetime
import numpy as np
import matplotlib
from trace import TraceLog


trace= TraceLog(1)
trace.save_event(0,0,0)
trace.add_thread()
trace.save_event(1,0,0)
trace.save_event(2,0,1)
trace.save_event(0,1,1)
trace.save_event(1,1,1)
trace.add_thread()
trace.save_event(2,1,2)
trace.save_event(0,0,3)
trace.save_event(3,1,1)
trace.save_event(0,2,1)
trace.save_event(1,2,1)

trace.plot_events()
'''
import plotly.express as px
import pandas as pd
import datetime
import time

tiempo= datetime.datetime.now()

print (datetime.datetime.now())

time.sleep(3)

df=[]
df.append(dict(Task="Job A", Start=tiempo, Finish=datetime.datetime.now(), Completion_pct=50))
df.append( dict(Task="Job B", Start=tiempo, Finish=datetime.datetime.now(), Completion_pct=25))
df.append(dict(Task="Job C", Start=tiempo, Finish=datetime.datetime.now(), Completion_pct=75))

fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Completion_pct")
fig.update_yaxes(autorange="reversed")
fig.show()

'''

# Fixing random state for reproducibility
np.random.seed(19680801)

# create random data
#data1 = np.random.random([6,7])
list1=[]
list1=[np.random.random(5)]

list1=[np.append(list1, [4])] # agregar un nuevo valor a la lista
print(len(list1))
print(list1)

list2=[np.random.random(6)]
list3=[np.random.random(6)]
list4=[np.random.random(6)]
list5=[np.random.random(6)]
list6=[np.random.random(6)]

print(np.concatenate((list1,list2, list3, list4, list5, list6))) # tienen que tener la misma dimension
data1=np.concatenate((list1,list2, list3, list4, list5, list6))

# set different colors for each set of positions
colors1 = ['C{}'.format(i) for i in range(6)]
print(colors1)

# set different line properties for each set of positions
# note that some overlap
lineoffsets1 = [0, 1, 2, 3, 4, 5]
linelengths1 = [1, 1, 1, 1, 1, 1]

#fig, axs = plt.subplots(2, 2)

# create a horizontal plot
plt.eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
                    linelengths=linelengths1)

# create a vertical plot
#axs[1, 0].eventplot(data1, colors=colors1, lineoffsets=lineoffsets1,
#                    linelengths=linelengths1, orientation='vertical')

# create another set of random data.
# the gamma distribution is only used fo aesthetic purposes
#data2 = np.random.gamma(4, size=[60, 50])

# use individual values for the parameters this time
# these values will be used for all data sets (except lineoffsets2, which
# sets the increment between each data set in this usage)
#colors2 = 'black'
#lineoffsets2 = 1
#linelengths2 = 1

# create a horizontal plot
#axs[0, 1].eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
#                    linelengths=linelengths2)


# create a vertical plot
#axs[1, 1].eventplot(data2, colors=colors2, lineoffsets=lineoffsets2,
#                    linelengths=linelengths2, orientation='vertical')

#plt.show()
'''
