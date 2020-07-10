from socket import *
import time
import base64
import ecdsa
import codecs
import json


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
            print("ok")

    def send_transaction(self, addr_to, amount):
        #For fast debugging
        #amount = ""
        #addr_to = ""

        if len(self.privateKey) == 64 and self.amount <= float(amount):
            timeS = str(round(time.time()))
            signature, message = self.sign_ECDSA_msg(timeS)
            s = socket(AF_INET, SOCK_STREAM)
            server_address = ('localhost', 1111)
            s.connect(server_address)
            print(timeS)
            print(self.publicKey)
            print(addr_to)
            print(message)
            msg = '{"action": "new_transaction", "transac":[{ "timestamp": "'+timeS+'", "from" : "' + self.publicKey + '", "to" : "' + addr_to + '", "amount": "' + amount + '", "signature" : "' + signature.decode() + '", "message": "' + message.decode() + '"}]}'
            s.send(msg.encode())
            print(msg)
        else:
            print("Wrong address or key length! Verify and try again.")

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


print("""=========================================\n
        Wallet - v0.0.0\n
       =========================================\n\n
        Make sure you are using the latest version or you may end in
        a parallel chain.\n\n\n""")
# need a request to server for the wallet version supported

response = input("""What do you want to do?
        1. Generate new wallet
        2. Connect to a wallet\n""")

if response == "2":
    public_addr = input("From: introduce your wallet address (public key)\n")
    private_key = input("Introduce your private key\n")
    # For fast debugging
    #public_addr = ""
    #private_key = ""
    my_wallet = Wallet(public_addr, private_key)
    my_wallet.connect_wallet()
if response == "1":
    my_wallet = Wallet()
    my_wallet.create_new_wallet()

response = 0
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
        my_wallet.check_transactions()
