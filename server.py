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


def create_chain_from_dump(chain_dump, walletKeyServer):
    generated_blockchain = Blockchain(walletKeyServer)
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
        s = MySocket()
        print("envoie sur le noeud :", node)
        s.connectTo(server_address)
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
        #print("[+] Nouveau thread pour %s %s" % (self.clientsocket, self.client,))

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
                        for block in blockchain.chain:
                            chain_data.append(block.__dict__)
                            chain = json.dumps({"length": len(chain_data),
                                                "chain": chain_data,
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

                        blockchain.add_new_transaction(tx_data)
                        self.clientsocket.send(b'Success')
                    if msg['action'] == "pending_tx":
                        self.clientsocket.send(str.encode(json.dumps(blockchain.unconfirmed_transactions)))
                    if msg['action'] == "mine":
                        result = blockchain.mine()
                        if not result:
                            self.clientsocket.send(b'No transactions to mine')
                        else:
                            # send block the others servers
                            chain_length = len(blockchain.chain)
                            consensus()
                            if chain_length == len(blockchain.chain):
                                # announce the recently mined block to the network
                                announce_new_block(blockchain.get_last_block)
                            self.clientsocket.send(
                                str.encode("Block #{} is mined.".format(blockchain.get_last_block.index)))
                    if msg['action'] == 'register_node':
                        print('Un nouveau serveur se joins à la blockchain !')
                        data = msg['data'][0]  # fixme
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
                elif len(r) == 0:
                    self.stop(ErrorLevels.ERROR, "La connection a été abandonnée")

        except Exception as e:
            #print("error while  " + str(e))
            self.stop(ErrorLevels.OK, "Le client a fermé la connection")

    def stop(self, error_level, error_msg):
        self.running = False
        self.close_connection()
        self.exit_callback(self, error_level, error_msg)

    def close_connection(self):
        self.running = False
        self.clientsocket.close()
        #print(f"Fin de la communication avec {self.client}")


class Server(threading.Thread):
    def __init__(self, Port):
        threading.Thread.__init__(self)
        self.client_pool = []
        self.running = True
        self.socket = MySocket()
        self.socket.bind(('localhost', Port))
        self.socket.settimeout(0.5)

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

    def close(self):
        self.running = False


walletKeyServer = generate_ECDSA_keys()
blockchain = Blockchain(walletKeyServer)
blockchain.create_genesis_block()
peers = set()
register_in_network = False
Port = 1111
serveur = Server(Port)
serveur.start()

while True:
    msg = input(">> ")
    if msg == 'see_peers':
        for peer in peers:
            print(peer)
    if msg == "see_clients":
        for client in serveur.client_pool:
            print(client)
    if msg == 'register_to_network' and not register_in_network:
        addr = input("IP of a node server >> ")
        s = socket(AF_INET, SOCK_STREAM)
        server_address = (addr, 1111)
        s.connect(server_address)
        hostname = gethostname()
        msg = '{"action": "register_node", "data": [{"IP": "' + gethostbyname(hostname) + '", "port": "1111"}]}'
        s.send(msg.encode())
        r = recvall(s)
        data = json.loads(r.decode("utf-8"))
        if data:
            chain_dump = data['chain']
            blockchain = create_chain_from_dump(chain_dump, walletKeyServer)
            peers.update(data['peers'])
            print('Registration on the network successful')
            register_in_network = True
        s.close()
    if msg == 'chain_len':
        print(len(blockchain.chain))
    if msg == 'close':
        serveur.close()
