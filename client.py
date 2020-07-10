# coding: utf-8

import mySocket
import threading


s = mySocket.socket(mySocket.AF_INET, mySocket.SOCK_STREAM)
server_address = ('localhost', 1111)
s.connect(server_address)

while 1:
    msg = input(">> ")  # utilisez raw_input() pour les anciennes versions python
    s.send(msg.encode())
    data = s.recv(1000000)
    if data:
        print('Received', repr(data))