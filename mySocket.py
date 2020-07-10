from socket import *

class MySocket(socket):

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None, name=None):
        super().__init__(family, type, proto, fileno)

    def connectTo(self, addr):
        server_address = (addr, 1111)
        self._sock.connect(server_address)

    def sendMsg(self, msg):
        self._sock.send(msg.encode())

    def sendMsgEncode(self, msg):
        self._sock.send(msg)
