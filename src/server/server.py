# coding: utf-8
from socket_server.mySocket import MySocket
from myPeer.myPeer import Peer
from block.block import Block
from client.client import ClientThread
from socket import *
import threading
import json
import time


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

    def recvall(self, sock,timeout=2):
        sock.setblocking(0)
        part = b''
        data = b''
        begin = time.time()
        while 1:
            # if you got some data, then break after wait sec
            if part and time.time() - begin > timeout:
                break
            # if you got no data at all, wait a little longer
            elif time.time() - begin > timeout * 2:
                break
            try:
                part = sock.recv(8192)
                if part:
                    data += part
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return data
    def close(self):
        self.running = False

    def create_chain_from_dump(self, chain_dump):
        for idx, block_data in enumerate(chain_dump):
            block = Block(index=int(block_data["index"]),
                          transactions=json.loads(block_data["transactions"]),
                          timestamp=block_data["timestamp"],
                          previous_hash=block_data["previous_hash"],
                          difficulty=int(block_data["difficulty"]),
                          nonce=int(block_data["nonce"]),
                          reward=float(block_data["reward"]),
                          gaslimit=int(block_data["gaslimit"]),
                          gasused=int(block_data["gasused"]),
                          size=int(block_data["size"]),
                          extra=block_data["extra"],
                          fees=float(block_data["fees"]),
                          )
            proof = block_data['hash']
            added = self.blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
                return False
        return True
