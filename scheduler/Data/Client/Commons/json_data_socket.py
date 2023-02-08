import json
import socket

## helper functions ##

def _send(socket_, data):
  try:
    serialized = json.dumps(data)
  except (TypeError, ValueError) as e:
    raise Exception('You can only send JSON-serializable data')
  # send the length of the serialized data first
  size_data= str(len(serialized)) + '\n'
  socket_.send(bytes(size_data, 'utf-8'))
  # send the serialized data
  socket_.send(bytes(serialized, 'utf-8'))

def _recv(socket_):
  # read the length of the data
  length_str = ''
  char = socket_.recv(1).decode('utf-8')
  while char != '\n':
    length_str += str(char)
    char = socket_.recv(1).decode('utf-8')
  total = int(length_str)
  # read data from socket
  data = socket_.recv(total).decode('utf-8')
  try:
    deserialized = json.loads(data)
  except (TypeError, ValueError) as e:
    raise Exception('Data received was not in JSON format')
  return deserialized