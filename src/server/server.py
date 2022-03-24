# coding: utf-8
from socket_server.mySocket import MySocket
from myPeer.myPeer import Peer
from block.block import Block
from client.client import ClientThread
from socket import *
import threading
import json


class ErrorLevels:
    OK = "OK"
    ERROR = "ERROR"


class Server(threading.Thread):
    def __init__(self, port, ip, blockchain):
        threading.Thread.__init__(self)
        self.client_pool = []
        self.running = True
        self.socket = MySocket()
        self.socket.bind((ip, int(port)))
        self.socket.settimeout(0.5)
        self.register_in_network = False
        self.Port = int(port)
        self.blockchain = blockchain
        self.peer = Peer()
        self.ip = ip

    def client_handling_stopped(self, client, error_level, error_msg):
        self.clean_up()

    def clean_up(self):
        self.client_pool = [client for client in self.client_pool if client.running]

    def log_connection_amount(self):
        print(f"Il y a maintenant {len(self.client_pool)} client(s) connecté(s)")

    def run(self):
        print('listening on port:', self.Port)
        self.socket.listen(10000)
        if not self.register_in_network:
            self.peer.add_peer(self.socket.getsockname())
        while self.running:
            try:
                idSocket, client = self.socket.accept()
                newthread = ClientThread(idSocket, client, self.client_handling_stopped, self.blockchain, self.peer,
                                         self.socket.getsockname())
                newthread.start()
                self.client_pool.append(newthread)
                self.log_connection_amount()
            except timeout:
                continue

    def auto_peer(self, addr, port):
        print('auto peer')
        s = socket(AF_INET, SOCK_STREAM)
        server_address = (addr, int(port))
        s.connect(server_address)
        msg = '{"action": "register_node", "data": [{"IP": "' + self.ip + '", "port": "' + str(self.Port) + '"}]}'
        s.send(msg.encode())
        r = self.recvall(s)
        data = json.loads(r.decode("utf-8"))
        if data:
            chain_dump = data['chain']
            self.create_chain_from_dump(chain_dump)
            for peer in data['peers']:
                self.peer.add_peer(tuple(peer))
            self.register_in_network = True
        s.close()

    def recvall(self, sock):
        BUFF_SIZE = 2048  # 1 KiB
        data = b''
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            if len(part) < BUFF_SIZE:
                # either 0 or end of data
                break
        return data

    def close(self):
        self.running = False

    def create_chain_from_dump(self, chain_dump):
        for idx, block_data in enumerate(chain_dump):
            block = Block(int(block_data["index"]),
                          json.loads(block_data["transactions"]),
                          block_data["timestamp"],
                          block_data["previous_hash"],
                          "",
                          int(block_data["nonce"]))

            proof = block_data['hash']
            added = self.blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
                return False
        return True
