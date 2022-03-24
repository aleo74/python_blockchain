# coding: utf-8
import json
import time
from mySocket import MySocket
from socket import *
import threading
from blockchain import Blockchain
from block import Block
import base64
import ecdsa
import sqlite3
from sqlite3 import Error
import pathlib
import os


def create_chain_from_dump(chain_dump, walletKeyServer):
    generated_blockchain = Blockchain(walletKeyServer)
    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data["index"],
                      json.loads(block_data["transactions"]),
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      "",
                      block_data["nonce"])
        if block.index == 0:
            continue  # skip genesis block

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
        s = MySocket()
        print("envoie sur le noeud :", node)
        s.connectTo(node)
        msg = '{"action": "get_chain"}'
        s.send(msg.encode())
        r = s.recvall()
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


def generate_ECDSA_keys():
    filename = input("Write the name of your new address: ") + ".txt"
    try:
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            public_key  = lines[1].split(": ")[1]
    except FileNotFoundError:
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)  # this is your sign (private key)
        private_key = sk.to_string().hex()  # convert your private key to hex
        vk = sk.get_verifying_key()  # this is your verification key (public key)
        public_key = vk.to_string().hex()
        # we are going to encode the public key to make it shorter
        public_key = base64.b64encode(bytes.fromhex(public_key))
        with open(filename, "w") as f:
            f.write("Private key: {0}\nWallet address / Public key: {1}".format(private_key, public_key.decode()))
        print("Your new address and private key are now in the file {0}".format(filename))
        print("copy this file to a secure directory, and delete your private key from the original")
        public_key = public_key.decode()
    return public_key


def announce_new_block(block):
    for peer in peers:
        s = MySocket()
        my_new_block = json.dumps(block.__dict__, sort_keys=True)
        msg = '{"action" : "add_block", "data" : ' + my_new_block + '}'
        s.connectTo(peer)
        s.sendMsg(msg)
        s.close()


class ErrorLevels:
    OK = "OK"
    ERROR = "ERROR"


# Fixme : need a way to move this on mySocket class
def recvall(sock):
    BUFF_SIZE = 2048  # 1 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data


class ClientThread(threading.Thread, MySocket):

    def __init__(self, socket, client, exit_callback, server=False):
        threading.Thread.__init__(self)
        self.clientsocket = socket
        self.client = client
        self.exit_callback = exit_callback
        self.running = True
        self.server = server

    def run(self):
        try:
            while self.running:
                r = recvall(self.clientsocket)
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
                        chain_data.append(blockchain.get_chain())
                        chain = json.dumps({"length": len(chain_data),
                                            "chain": blockchain.get_chain(),
                                            "peers": list(peers)})
                        self.clientsocket.send(str.encode(chain))
                    if msg['action'] == "new_transaction":
                        tx_data = {}
                        if 'data' in msg:
                            tx_data['data'] = []
                            for data in msg['data']:
                                data["timestamp"] = time.time()
                                tx_data['data'].append(data)

                        if 'transac' in msg:
                            tx_data['transac'] = []
                            for transac in msg['transac']:
                                transac["timestamp"] = time.time()
                                tx_data['transac'].append(transac)

                        mining = blockchain.add_new_transaction(tx_data)
                        self.clientsocket.send(bytes([blockchain.get_last_block.index]))
                        if mining:
                            blockchain.mine()
                            chain_length = len(blockchain.chain)
                            consensus()
                            if chain_length == len(blockchain.chain):
                                # announce the recently mined block to the network
                                announce_new_block(blockchain.get_last_block)

                    if msg['action'] == "pending_tx":
                        self.clientsocket.send(str.encode(json.dumps(blockchain.unconfirmed_transactions)))
                    if msg['action'] == 'register_node':
                        print('Un nouveau serveur se joins à la blockchain !')

                        data = msg['data'][0]  # fixme
                        if not data['IP']:
                            print('error')
                            self.clientsocket.send(b'error')
                            break
                        print('ici')
                        peers.add(data['IP'])
                        print(peers)
                        chain_data = []
                        chain_data.append(blockchain.get_chain())
                        chain = json.dumps({"length": len(chain_data),
                                            "chain": blockchain.get_chain(),
                                            "peers": list(peers)})
                        self.clientsocket.send(str.encode(chain))
                    if msg['action'] == 'add_block':
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
                    if msg['action'] == 'get_block':
                        if 'num_block' in msg:
                            self.clientsocket.send(
                                str.encode(json.dumps(blockchain.get_block_by_index(msg['num_block']))))
                        if 'hash' in msg:
                            self.clientsocket.send(str.encode(json.dumps(blockchain.find_block_by_hash(msg['hash']))))
                    if msg['action'] == 'see_peers':
                        peer = ''.join(peers)
                        print(peer)
                        self.clientsocket.send(b''.peer)
                    if msg['action'] == "chain_len":
                        len_chain = str(blockchain.get_len_chain())
                        self.clientsocket.send(str.encode(len_chain))
                elif len(r) == 0:
                    self.stop(ErrorLevels.ERROR, "La connection a été abandonnée")

        except Exception as e:
            self.stop(ErrorLevels.OK, "Le client a fermé la connection")

    def stop(self, error_level, error_msg):
        self.running = False
        self.close_connection()
        self.exit_callback(self, error_level, error_msg)

    def close_connection(self):
        self.running = False
        self.clientsocket.close()


class Server(threading.Thread):
    def __init__(self, Port):
        threading.Thread.__init__(self)
        self.client_pool = []
        self.running = True
        self.socket = MySocket()
        self.socket.bind(('localhost', Port))
        self.socket.settimeout(0.5)
        self.register_in_network = False

    def client_handling_stopped(self, client, error_level, error_msg):
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
                idSocket, client = self.socket.accept()
            except timeout:
                continue
            newthread = ClientThread(idSocket, client, self.client_handling_stopped)
            newthread.start()
            self.client_pool.append(newthread)
            self.log_connection_amount()

    def auto_peer(self, addr, port):
        print('auto peer')
        s = socket(AF_INET, SOCK_STREAM)
        server_address = (addr, 1111)
        s.connect(server_address)
        hostname = "127.0.0.1" # IP su serveur
        msg = '{"action": "register_node", "data": [{"IP": "' + hostname + '", "port": "' + str(port) + '"}]}'
        s.send(msg.encode())
        r = recvall(s)
        data = json.loads(r.decode("utf-8"))

        if data:
            chain_dump = data['chain']
            global blockchain
            global peers
            KeyServer = blockchain.address_wallet_miner
            blockchain = create_chain_from_dump(chain_dump, KeyServer)
            peers.update(data['peers'])
            self.register_in_network = True
        s.close()

    def close(self):
        self.running = False

# SQLite3

sql_create_tasks_table = """CREATE TABLE IF NOT EXISTS blocks (
                                    id integer PRIMARY KEY,
                                    num_block integer NOT NULL,
                                    hash text,
                                    transactions text,
                                    timestamp text,
                                    previous_hash text not null,
                                    nonce integer
                                );"""

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        return True
    except Error as e:
        print(e)

second_server = 0
if second_server == 0:
    fichier_db = r".\db\pythonsqlite.db"
else:
    fichier_db = r".\db\pythonsqlite2.db"
if os.path.exists(fichier_db):
    os.remove(fichier_db)
conn = create_connection(fichier_db)
if conn is not None:
    if create_table(conn, sql_create_tasks_table):
        walletKeyServer = generate_ECDSA_keys()
        blockchain = Blockchain(walletKeyServer, fichier_db)
        blockchain.create_genesis_block()
        peers = set()
        register_in_network = False
        if second_server == 0:
            Port = 1111
            serveur = Server(Port)
            serveur.start()
            #serveur.auto_peer("127.0.0.1", Port)
        else:
            Port = 1110
            serveur = Server(Port)
            serveur.start()
            serveur.auto_peer("127.0.0.1", Port)
