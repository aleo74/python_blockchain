from socket import *
import time
import base64
import ecdsa
import codecs
import json


class Wallet():

    def __init__(self, nodeAddress="", publicKey="", privateKey=""):
        self.publicKey = publicKey
        self.nodeAddress = nodeAddress
        self.privateKey = privateKey
        self.connect = False
        self.amount = 0.0

    def check_transactions(self):
        s = socket(AF_INET, SOCK_STREAM)
        server_address = (self.nodeAddress, 1111)
        s.connect(server_address)
        msg = '{"action": "get_chain"}'
        s.send(msg.encode())
        data = self.recvall(s)
        amount = 0.0
        if data and self.connect:
            all_block = json.loads(data)
            for block in all_block['chain']:
                if block['index'] == 0:
                    continue
                for transac in block['transactions']['transac']:
                    if transac['vout']['receiver'] == self.publicKey:
                        amount += float(transac['vout']['amount'])
                    signature, message = self.sign_ECDSA_msg(str(transac['vout']['timestamp']))
                    if signature == transac['vout']['signature'] and message == transac['vout']['message']:
                        amount -= float(transac['vout']['amount'])
            self.amount = amount
        #print(self.amount)

    def create_new_wallet(self):
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)  # this is your sign (private key)
        self.privateKey = sk.to_string().hex()  # convert your private key to hex
        vk = sk.get_verifying_key()  # this is your verification key (public key)
        self.publicKey = vk.to_string().hex()
        # we are going to encode the public key to make it shorter
        self.publicKey = base64.b64encode(bytes.fromhex(self.publicKey))

        filename = 'my_address.txt' #input("Write the name of your new address: ") + ".txt"
        with open(filename, "w") as f:
            f.write(
                "Private key: {0}\nWallet address / Public key: {1}".format(self.privateKey, self.publicKey.decode()))
        #print("Your new address and private key are now in the file {0}".format(filename))
        return self.publicKey.decode()

    def connect_wallet(self):
        decode_hex = codecs.getdecoder("hex_codec")
        self.privateKey32 = decode_hex(self.privateKey)[0]
        key = ecdsa.SigningKey.from_string(self.privateKey32, curve=ecdsa.SECP256k1)
        vk = key.get_verifying_key()
        public_key = vk.to_string().hex()
        public_key = base64.b64encode(bytes.fromhex(public_key)).decode()

        if public_key == self.publicKey:
            self.connect = True
            return self.publicKey
        else:
            return False

    def send_transaction(self, addr_to, amount):

        if len(self.privateKey) == 64 and self.amount <= float(amount):
            timeS = str(round(time.time()))
            signature, message = self.sign_ECDSA_msg(timeS)
            s = socket(AF_INET, SOCK_STREAM)
            server_address = (self.nodeAddress, 1111)
            s.connect(server_address)
            self.amount = self.amount - float(amount)
            msg = '{"action": "new_transaction", "transac":[{ "timestamp": "'+timeS+'", "from" : "' + self.publicKey + '", "to" : "' + addr_to + '", "amount": "' + amount + '", "signature" : "' + signature.decode() + '", "message": "' + message.decode() + '"}]}'
            s.send(msg.encode())
            return msg
        else:
            return False

    def sign_ECDSA_msg(self, timeS):
        message = timeS
        message = message.encode()
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(self.privateKey), curve=ecdsa.SECP256k1)
        signature = base64.b64encode(sk.sign(message))
        return signature, message

    def recvall(self, sock):
        BUFF_SIZE = 1024  # 1 KiB
        data = b''
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            if len(part) < BUFF_SIZE:
                # either 0 or end of data
                break
        return data

    def getPublicKey(self):
        return self.publicKey

    def getAmount(self):
        return self.amount
