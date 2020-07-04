# coding: utf-8
from utils import *
import json
import time
import sys
from socket import *
import threading
from blockchain import Blockchain
from block import Block

def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain

def consensus():
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)
    for node in peers:
        s = socket(AF_INET, SOCK_STREAM)
        print("envoie sur le noeud :", node)
        server_address = ("localhost", 1111)
        s.connect(server_address)
        msg = '{"action": "get_chain"}'
        s.send(msg.encode())
        r = s.recv(1024)
        data = json.loads(r.decode("utf-8"))
        if data:
            length = data['length']
            chain = data['chain']
            if length > current_len and blockchain.check_chain_validity(chain):
                current_len = length
                longest_chain = chain
        s.close()

    if longest_chain:
        blockchain = longest_chain
        return True
    return False

def announce_new_block(block):

    for peer in peers:
        s = socket(AF_INET, SOCK_STREAM)
        server_address = ("localhost", 1111)
        my_new_block = json.dumps(block.__dict__, sort_keys=True)
        msg = '{"action" : "add_block", "data" : '+my_new_block+'}'
        s.connect(server_address)
        s.send(msg.encode())
        s.close()

class ErrorLevels:
    OK = "OK"
    ERROR = "ERROR"

blockchain = Blockchain()
blockchain.create_genesis_block()
peers = set()

class ClientThread(threading.Thread):

    def __init__(self, client, port, exit_callback, server = False):
        threading.Thread.__init__(self)
        self.clientsocket = client
        self.port = port
        self.exit_callback = exit_callback
        self.running = True
        self.server = server
        print("[+] Nouveau thread pour %s %s" % (self.clientsocket, self.port,))

    def run(self):
        try:
            while self.running:
                r = self.clientsocket.recv(2048)
                if r:
                    msg = json.loads(r.decode("utf-8"))
                    if not msg['action']:
                        self.running = False
                        self.clientsocket.close()
                        break
                    if msg['action'] == "quit":
                        self.clientsocket.send(b'you quit the server')
                        break
                    if msg['action'] == "get_chain":
                        chain_data = []
                        for block in blockchain.chain:
                            chain_data.append(block.__dict__)
                            chain = json.dumps({"length": len(chain_data),
                                                "chain": chain_data,
                                                "peers": list(peers)})
                        self.clientsocket.send(str.encode(chain))
                    if msg['action'] == "new_transaction":
                        tx_data = msg['data'][0]
                        required_fields = ["author", "content"]

                        for field in required_fields:
                            if not tx_data[field]:
                                self.clientsocket.send(b'Invalid transaction data')

                        tx_data["timestamp"] = time.time()

                        blockchain.add_new_transaction(tx_data)
                        self.clientsocket.send(b'Success')
                    if msg['action'] == "pending_tx":
                        self.clientsocket.send(str.encode(json.dumps(blockchain.unconfirmed_transactions)))
                    if msg['action'] == "mine":
                        result = blockchain.mine()
                        if not result:
                            self.clientsocket.send(b'No transactions to mine')
                        else:
                            #send block the others servers
                            chain_length = len(blockchain.chain)
                            consensus()
                            if chain_length == len(blockchain.chain):
                                # announce the recently mined block to the network
                                announce_new_block(blockchain.get_last_block)
                            self.clientsocket.send(str.encode("Block #{} is mined.".format(blockchain.get_last_block.index)))
                    if msg['action'] == 'register_node':
                        print('Un nouveau serveur se joins à la blockchain !')
                        data = msg['data'][0]
                        if not data['IP']:
                            print('error')
                            self.clientsocket.send(b'error')
                            break
                        peers.add(data['IP'])
                        chain_data = []
                        for block in blockchain.chain:
                            chain_data.append(block.__dict__)
                            chain = json.dumps({"length": len(chain_data),
                                                "chain": chain_data,
                                                "peers": list(peers)})
                        self.clientsocket.send(str.encode(chain))
                    if msg['action'] == 'add_block':
                        print("nous avons reçu un nouveau block !")
                        block_data = msg['data']
                        block = Block(block_data["index"],
                                      block_data["transactions"],
                                      block_data["timestamp"],
                                      block_data["previous_hash"],
                                      block_data["nonce"])

                        proof = block_data['hash']
                        added = blockchain.add_block(block, proof)

                        if not added:
                            print("The block was discarded by the node")

                        print("Block added to the chain")
                elif len(r) == 0:
                    self.stop(ErrorLevels.ERROR, "La connection a été abandonnée")
        except ConnectionAbortedError:
            if self.running:
                self.stop(ErrorLevels.ERROR, "La connection a été abandonnée")
            else:
                return
        self.stop(ErrorLevels.OK, "Le client a fermé la connection")

    def stop(self, error_level, error_msg):
        self.running = False
        self.close_connection()
        self.exit_callback(self, error_level, error_msg)

    def close_connection(self):
        self.running = False
        self.clientsocket.close()
        print(f"Fin de la communication avec {self.port}")




class Server(threading.Thread):
    def __init__(self, Port):
        threading.Thread.__init__(self)
        self.client_pool = []
        self.running = True
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.bind(('localhost', Port))
        self.socket.settimeout(0.5)

    def client_handling_stopped(self, client, error_level, error_msg):
        print(f"Le gérant de {client.port} s'est arrêté avec le niveau d'erreur {error_level} ({error_msg})")
        self.clean_up()

    def clean_up(self):
        self.client_pool = [client for client in self.client_pool if client.running]

    def log_connection_amount(self):
        print(f"Il y a maintenant {len(self.client_pool)} client(s) connecté(s)")

    def run(self):
        print('listening on port:', Port)
        self.socket.listen(10000)
        while self.running:
            try:
                ip, port = self.socket.accept()
            except timeout:
                continue
            newthread = ClientThread(ip, port, self.client_handling_stopped)
            newthread.start()
            self.client_pool.append(newthread)
            self.log_connection_amount()

    def close(self):
        self.running = False


register_in_network = False


Port = 1000

serveur = Server(Port)
serveur.start()

while True:
    msg = input(">> ")
    if msg == 'see_peers':
        for peer in peers:
            print(peer)
    if msg == 'register_to_network' and not register_in_network:
        addr = input(">> ")
        s = socket(AF_INET, SOCK_STREAM)
        server_address = ('localhost', 1111)
        s.connect(server_address)
        hostname = gethostname()
        msg = '{"action": "register_node", "data": [{"IP": "'+gethostbyname(hostname)+'", "port": "1111"}]}'
        s.send(msg.encode())
        r = s.recv(1024)
        data = json.loads(r.decode("utf-8"))
        if data:
            print(data)
            chain_dump = data['chain']
            blockchain = create_chain_from_dump(chain_dump)
            peers.update(data['peers'])
            print('Registration on the network successful')
            register_in_network = True
        s.close()
    if msg == 'close':
        serveur.close()

