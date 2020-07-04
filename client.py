# coding: utf-8

import socket
import threading


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', 1000)
s.connect(server_address)

while 1:
    msg = input(">> ")  # utilisez raw_input() pour les anciennes versions python
    s.send(msg.encode())
    data = s.recv(1024)
    if data:
        print('Received', repr(data))