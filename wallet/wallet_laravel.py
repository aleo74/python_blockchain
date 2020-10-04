from socket import *
import time
import base64
import ecdsa
import codecs
import json
import sys
import urllib.request

version = 'v0.2'
hash = ''

class Wallet():

    def __init__(self, publicKey="", privateKey=""):
        self.publicKey = publicKey
        self.privateKey = privateKey
        self.connect = False
        self.amount = 0.0

    def check_transactions(self):
        s = socket(AF_INET, SOCK_STREAM)
        server_address = ('localhost', 1111)
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
                    print(transac)
                    if transac['vout']['receiver'] == self.publicKey:
                        amount += float(transac['vout']['amount'])
                    signature, message = self.sign_ECDSA_msg(str(transac['vout']['timestamp']))
                    if signature == transac['vout']['signature'] and message == transac['vout']['message']:
                        amount -= float(transac['vout']['amount'])
            self.amount = amount
        print(self.amount)

    def create_new_wallet(self):
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)  # this is your sign (private key)
        self.privateKey = sk.to_string().hex()  # convert your private key to hex
        vk = sk.get_verifying_key()  # this is your verification key (public key)
        self.publicKey = vk.to_string().hex()
        # we are going to encode the public key to make it shorter
        self.publicKey = base64.b64encode(bytes.fromhex(self.publicKey))

        filename = input("Write the name of your new address: ") + ".txt"
        with open(filename, "w") as f:
            f.write(
                "Private key: {0}\nWallet address / Public key: {1}".format(self.privateKey, self.publicKey.decode()))
        print("Your new address and private key are now in the file {0}".format(filename))
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
            #print("ok")

    def send_transaction(self, addr_to, amount):
        if len(self.privateKey) == 64 and self.amount <= float(amount):
            timeS = str(round(time.time()))
            signature, message = self.sign_ECDSA_msg(timeS)
            s = socket(AF_INET, SOCK_STREAM)
            server_address = ('localhost', 1111)
            s.connect(server_address)
            msg = '{"action": "new_transaction", "transac":[{ "timestamp": "'+timeS+'", "from" : "' + self.publicKey + '", "to" : "' + addr_to + '", "amount": "' + amount + '", "signature" : "' + signature.decode() + '", "message": "' + message.decode() + '"}]}'
            s.send(msg.encode())
        else:
            return False

    def sign_ECDSA_msg(self, timeS):
        message = timeS
        message = message.encode()
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(self.privateKey), curve=ecdsa.SECP256k1)
        signature = base64.b64encode(sk.sign(message))
        return signature, message

    def get_block(self, id_block, id):
        s = socket(AF_INET, SOCK_STREAM)
        server_address = ('localhost', 1111)
        s.connect(server_address)
        msg = '{"action": "get_block", "num_block": '+id_block+'}'
        s.send(msg.encode())
        data = self.recvall(s)
        print(data)
        if data and self.connect:
            string = json.loads(data)
            my_data = json.loads(string['transactions'])
            for id_manga in my_data['data'][0]:
                if id_manga['id'] == id:
                    if 'address' in id_manga:
                        self.send_transaction(id_manga['address'], '0.002')
                        manga = id_manga
            print(json.dumps(manga))

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

    def post_data(self, data):
        if data and self.connect:
            s = socket(AF_INET, SOCK_STREAM)
            server_address = ('127.0.0.1', 1111)
            s.connect(server_address)
            msg = '{"action": "new_transaction", "data": ['+data+']}'
            s.send(msg.encode())
            data1 = s.recv(1000000)
            if data1:
                print(int.from_bytes(data1, byteorder='big'))



with urllib.request.urlopen("http://brandon-corporation.local/api/wallet_laravel_version") as url:
    s = url.read()
    response = json.loads(s)

if response:
    if response['version'] == version:
        if response['hash'] == hash:
            public_addr = sys.argv[2]
            private_key = sys.argv[1]

            index_block = sys.argv[3]
            id = sys.argv[4]

            if len(sys.argv) >= 6:
                data = json.dumps(json.loads(base64.b64decode(sys.argv[5])))
            else :
                data = False

            my_wallet = Wallet(public_addr, private_key)
            my_wallet.connect_wallet()

            if not data:
                my_wallet.get_block(index_block, id)

            else:
                my_wallet.post_data(data)

