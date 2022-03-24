import sqlite3
from sqlite3 import Error
import os
import argparse
import base64
import ecdsa
from blockchain.blockchain import Blockchain
from server.server import Server


def generate_ECDSA_keys():
    filename = input("Write the name of your new address: ") + ".txt"
    try:
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            public_key = lines[1].split(": ")[1]
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', nargs='?', help='-ip : ip of server')
    parser.add_argument('-p', nargs='?', help='-p : port of server')
    args = parser.parse_args()
    fichier_db = r".\db\pythonsqlite.db"
    if os.path.exists(fichier_db):
        os.remove(fichier_db)

    conn = create_connection(fichier_db)
    if create_table(conn, sql_create_tasks_table):
        walletKeyServer = generate_ECDSA_keys()
        blockchain = Blockchain(walletKeyServer, fichier_db)
        blockchain.create_genesis_block()
        server = Server(args.p, args.ip, blockchain)
        server.start()


def restart():
    fichier_db = r".\db\pythonsqlite.db"
    conn = create_connection(fichier_db)
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', nargs='?', help='-ip : ip of server')
    parser.add_argument('-p', nargs='?', help='-p : port of server')
    args = parser.parse_args()
    if conn:
        walletKeyServer = generate_ECDSA_keys()
        blockchain = Blockchain(walletKeyServer, fichier_db)
        server = Server(args.p, args.ip, blockchain)
        server.start()


def join():
    fichier_db = r".\db\pythonsqlite2.db"
    if os.path.exists(fichier_db):
        os.remove(fichier_db)
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', nargs='?', help='-ip : ip of server')
    parser.add_argument('-p', nargs='?', help='-p : port of server')
    parser.add_argument('-jip', nargs='?', help='-p : port of server distant')
    parser.add_argument('-jp', nargs='?', help='-p : port of server distant')
    args = parser.parse_args()

    conn = create_connection(fichier_db)
    if create_table(conn, sql_create_tasks_table):
        walletKeyServer = generate_ECDSA_keys()
        blockchain = Blockchain(walletKeyServer, fichier_db)
        server = Server(args.p, args.ip, blockchain)
        server.auto_peer(args.jip, args.jp)
        server.start()


if __name__ == '__main__':
    main()
