import os
import sys
from functools import partial
import time

# Reemplaza linea de texto en un archivo       
def replace_line(file_name, line_num, text):
    lines = open(file_name, 'r').readlines()
    lines[line_num] = text
    out = open(file_name, 'w')
    out.writelines(lines)
    out.close()

filename= "/home/tf_parallelism.txt"
# Cambiar el paralelismo del fichero
replace_line(filename, 0, str(6) + " " + str(5) + "\n")