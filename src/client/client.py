import socket

from socket_server.mySocket import MySocket
from block.block import Block
from socket import *
import threading
import json
import time


class ErrorLevels:
    OK = "OK"
    ERROR = "ERROR"


class ClientThread(threading.Thread, MySocket):

    def __init__(self, socketclient, client, exit_callback, blockchain, peer, server=False):
        threading.Thread.__init__(self)
        self.clientsocket = socketclient
        self.client = client
        self.exit_callback = exit_callback
        self.running = True
        self.server = server
        self.blockchain = blockchain
        self.peers = peer

    def run(self):
        try:
            while self.running:
                r = self.recvall(self.clientsocket)
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
                        chain_data.append(self.blockchain.get_chain())
                        chain = json.dumps({"length": len(chain_data),
                                            "chain": chain_data,
                                            "peers": self.peers.get_peers()})
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

                        mining = self.blockchain.add_new_transaction(tx_data)
                        self.clientsocket.send(bytes([self.blockchain.get_last_block.index]))
                        if mining:
                            self.blockchain.mine()
                            chain_length = self.blockchain.get_size(self.blockchain.get_chain())
                            consensus = self.consensus()
                            if chain_length == self.blockchain.get_size(self.blockchain.get_chain()) and not consensus:
                                # announce the recently mined block to the network
                                self.announce_new_block(self.blockchain.get_last_block)
                    if msg['action'] == "pending_tx":
                        self.clientsocket.send(str.encode(json.dumps(self.blockchain.unconfirmed_transactions)))
                    if msg['action'] == 'register_node':
                        data = msg['data'][0]  # fixme
                        if not data['IP']:
                            print('error')
                            self.clientsocket.send(b'error')
                            break
                        self.peers.add_peer((data['IP'], int(data['port'])))
                        chain_data = []
                        chain_data.append(self.blockchain.get_chain())
                        chain = json.dumps({"length": len(chain_data),
                                            "chain": self.blockchain.get_chain(),
                                            "peers": list(self.peers.get_peers())})
                        self.clientsocket.send(str.encode(chain))
                    if msg['action'] == 'add_block':
                        block_data = msg['data']
                        block = Block(index=block_data["index"],
                                      transactions=json.loads(block_data["transactions"]),
                                      timestamp=block_data["timestamp"],
                                      previous_hash=block_data["previous_hash"],
                                      difficulty=block_data["difficulty"],
                                      reward=float(block_data["reward"]),
                                      extra='',
                                      fees=float(block_data["fees"]),
                                      size=block_data["size"],
                                      gaslimit=block_data["gaslimit"],
                                      gasused=block_data["gasused"],
                                      nonce=block_data["nonce"])

                        hash_received = block_data['hash']
                        added = self.blockchain.add_block(block, hash_received)

                        if not added:
                            msg = "The block was discarded by the node"
                        else:
                            msg = "True"
                        self.clientsocket.send(str.encode(msg))
                    if msg['action'] == 'get_block':
                        if 'num_block' in msg:
                            self.clientsocket.send(
                                str.encode(json.dumps(self.blockchain.get_block_by_index(msg['num_block']))))
                        if 'hash' in msg:
                            self.clientsocket.send(
                                str.encode(json.dumps(self.blockchain.find_block_by_hash(msg['hash']))))
                    if msg['action'] == 'see_peers':
                        self.clientsocket.send(str.encode(json.dumps({"peers": self.peers.get_peers()})))
                    if msg['action'] == "chain_len":
                        len_chain = str(self.blockchain.get_len_chain())
                        self.clientsocket.send(str.encode(len_chain))
                    if msg['action'] == "ping":
                        self.clientsocket.send(str.encode('True'))
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

    def announce_new_block(self, block):
        print('annonce block')
        for peer in self.peers.get_peers():
            if peer == self.server:
                print('mon propre server')
            else:
                s = socket(AF_INET, SOCK_STREAM)
                s.settimeout(1)
                print("envoie sur le noeud :", peer)
                try:
                    s.connect(peer)
                except OSError as exc:
                    print("Caught exception socket.error : %s" % exc)
                    self.peers.unset_peer(peer)
                except:  # Not recommended! To general!
                    self.peers.unset_peer(peer)
                    print("💀")
                else:
                    my_new_block = json.dumps(block.__dict__, sort_keys=True)
                    msg = '{"action" : "add_block", "data" : ' + my_new_block + '}'
                    s.send(msg.encode())
                    s.close()

    def consensus(self):
        longest_chain = None
        current_len = self.blockchain.get_size(self.blockchain.get_chain())
        for node in self.peers.get_peers():
            print(node)
            if node == self.server:
                print('mon propre server')
            else:
                s = socket(AF_INET, SOCK_STREAM)
                s.settimeout(1)
                print("envoie sur le noeud :", node)
                try:
                    s.connect(node)
                except OSError as exc:
                    print("Caught exception socket.error : %s" % exc)
                    self.peers.unset_peer(node)
                except:  # Not recommended! To general!
                    self.peers.unset_peer(node)
                    print("💀")
                else:
                    msg = '{"action": "get_chain"}'
                    s.send(msg.encode())
                    r = self.recvall(s)
                    data = json.loads(r.decode("utf-8"))
                    if data:
                        length = self.blockchain.get_size(data['chain'])
                        chain = data['chain']
                        # TODO a revoir
                        if length > current_len and self.blockchain.check_chain_validity(chain):
                            longest_chain = chain
                    s.close()


        if longest_chain:
            # TODO a refaire
            blockchain = longest_chain
            return True
        else:
            return False

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
