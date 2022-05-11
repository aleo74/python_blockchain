from socket import *
import time
import base64
import ecdsa
import codecs
import json
import sqlite3
from sqlite3 import Error
from time import sleep
from bech32 import bech32_encode, convertbits
import hashlib
import eth_keys, eth_utils, binascii, os

class Vout():
    def __init__(self, receiver, sender, amount, message, timestamp):
        self.receiver = receiver
        self.sender = sender
        self.amount = float(amount)
        self.signature = ''
        self.message = message
        self.timestamp = timestamp
        self.hash = ''

    @staticmethod
    def sign(transaction, private_key):
        signerPrivKey = private_key
        dict = transaction.__dict__
        strDict = str(dict)
        return signerPrivKey.sign_msg(strDict.encode('utf-8'))

    def generate_hash(self):
        self.hash = hashlib.sha256(
            (str(self.timestamp) + str(self.receiver) + str(self.sender) + str(self.message) + str(self.signature) + str(
                self.amount)).encode('utf-8')).hexdigest()


class Wallet():

    def __init__(self, address="", privateKey=""):
        self.publicKey = ''
        self.privateKey = privateKey
        self.address = address
        self.connect = False
        self.amount = 0.0

    def check_transactions(self):
        s = socket(AF_INET, SOCK_STREAM)
        server_address = ('127.0.0.1', 1122)
        s.connect(server_address)
        msg = '{"action": "get_chain"}'
        s.send(msg.encode())
        data = self.recvall(s)
        amount = 0.0
        if data and self.connect:
            all_block = json.loads(data)
            for block in all_block['chain'][0]:
                if int(block['index']) == 0:
                    continue
                transaction = json.loads(block['transactions'])
                for transac in transaction['transac']:
                    if transac['vout']['receiver'] == self.address:
                        amount += float(transac['vout']['amount'])
                    if transac['vout']['sender'] == self.address:
                        amount -= float(transac['vout']['amount'])
        msg = '{"action": "pending_tx"}'
        s.send(msg.encode())
        pendingData = self.recvall(s)
        if pendingData and self.connect:
            dataPending = json.loads(pendingData)
            if "transac" in dataPending:
                for transac in dataPending['transac']:
                    if transac['vout']['receiver'] == self.address:
                        amount += float(transac['vout']['amount'])
                    if transac['vout']['sender'] == self.address:
                        amount -= float(transac['vout']['amount'])
        self.amount = amount
        return self.amount

    def create_new_wallet(self):
        self.privateKey = eth_keys.keys.PrivateKey(os.urandom(32))
        self.publicKey = self.privateKey.public_key
        s = hashlib.new("sha256", str(self.publicKey).encode('utf-8')).digest()
        r = hashlib.new("ripemd160", s).digest()
        assert convertbits(r, 8, 5) is not None, "Unsuccessful bech32.convertbits call"
        self.address = bech32_encode("TC", convertbits(r, 8, 5))
        print(self.address)
        filename = input("Write the name of your new address: ") + ".txt"
        with open(filename, "w") as f:
            f.write("Private key: {0}\nWallet address / Public key: {1}\nyour address: {2}".format(self.privateKey,
                                                                                              self.publicKey,
                                                                                              self.address))
        print("Your new address and private key are now in the file {0}".format(filename))
        print("copy this file to a secure directory, and delete your private key from the original")
        return self.address

    def connect_wallet(self):
        self.privateKey = eth_keys.keys.PrivateKey(binascii.unhexlify(self.privateKey[2:]))
        public_key = self.privateKey.public_key
        s = hashlib.new("sha256", str(public_key).encode('utf-8')).digest()
        r = hashlib.new("ripemd160", s).digest()
        five_bit_r = convertbits(r, 8, 5)
        assert five_bit_r is not None, "Unsuccessful bech32.convertbits call"
        address = bech32_encode("TC", five_bit_r)

        if address == self.address:
            self.connect = True
            return True
        else:
            return False

    def send_transaction(self, addr_to, amount):
        if len(self.privateKey) == 64:
            s = socket(AF_INET, SOCK_STREAM)
            server_address = ('127.0.0.1', 1122)
            s.connect(server_address)
            message = ''
            vout = Vout(addr_to, self.address, amount, message, str(time.time()))
            signature = Vout.sign(vout, self.privateKey)
            vout.signature = str(signature)
            vout.generate_hash()
            msg = '{"action": "new_transaction", "transac":['+json.dumps(vout.__dict__)+']}'
            print(msg)
            s.send(msg.encode())
        else:
            print('NOPE')



    def recvall(self, sock):
        BUFF_SIZE = 1024  # 1 KiB
        data = b''
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            sleep(0.005)
            if len(part) < BUFF_SIZE:
                # either 0 or end of data
                break
        return data


print("""=========================================\n
        Wallet - v0.0.4\n
       =========================================\n\n
        Make sure you are using the latest version or you may end in
        a parallel chain.\n\n\n""")
# need a request to server for the wallet version supported

response = input("""What do you want to do?
        1. Generate new wallet
        2. Connect to a wallet\n""")



if response == "2":
    # public_addr = input("From: introduce your wallet address or public key\n")
    # private_key = input("Introduce your private key\n")
    # For fast debugging
    public_addr = "TC1d9sxn02q2f9hd3zy72d4r8e7zj0azmq02gszpt"
    private_key = "0x5f80a8070d9b9220a910f97120e3018d119c1335af9bae15071a0a6f2fad8df8"

    my_wallet = Wallet(public_addr, private_key)
    connect = my_wallet.connect_wallet()
    my_wallet.send_transaction('TC14cr0tntxhs358qwz0twwhupvczr2nf8klz03y0', 10)
    exit()
if response == "1":
    my_wallet = Wallet()
    my_wallet.create_new_wallet()
    connect = True

response = 0
if connect == True:
    while response not in ["1", "2", "3"]:
        response = input("""What do you want to do?
            1. Send coins to another wallet
            2. Check transactions\n""")
        if response == "1":
            addr_to = input("To: introduce destination wallet address\n")
            amount = input("Amount: number stating how much do you want to send\n")
            print("=========================================\n\n")
            print("Is everything correct?\n")
            print("To: {0}\nAmount: {1}\n".format(addr_to, amount))
            response = input("y/n\n")
            if response.lower() == "y":
                my_wallet.send_transaction(addr_to, amount)
        elif response == "2":
            amount = my_wallet.check_transactions()
            print(f"{amount:.4f}")
