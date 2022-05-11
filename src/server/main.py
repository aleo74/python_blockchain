import sqlite3
from sqlite3 import Error
import os
import argparse
import base64
import ecdsa
import hashlib
from blockchain.blockchain import Blockchain
from server.server import Server
from bech32 import bech32_encode, convertbits
import eth_keys, eth_utils, binascii, os


def generate_ECDSA_keys():
    filename = "server.txt"
    try:
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            public_key = lines[1].split(": ")[1]
            public_key_bytes = bytes.fromhex(public_key)
            s = hashlib.new("sha256", public_key_bytes).digest()
            r = hashlib.new("ripemd160", s).digest()
            five_bit_r = convertbits(r, 8, 5)
            assert five_bit_r is not None, "Unsuccessful bech32.convertbits call"
            address = bech32_encode("TC", five_bit_r)
    except FileNotFoundError:
        privateKey = eth_keys.keys.PrivateKey(os.urandom(32))
        publicKey = privateKey.public_key
        s = hashlib.new("sha256", str(publicKey).encode('utf-8')).digest()
        r = hashlib.new("ripemd160", s).digest()
        assert convertbits(r, 8, 5) is not None, "Unsuccessful bech32.convertbits call"
        address = bech32_encode("TC", convertbits(r, 8, 5))

        filename = input("Write the name of your new address: ") + ".txt"
        with open(filename, "w") as f:
            f.write("Private key: {0}\nWallet address / Public key: {1}\nyour address: {2}".format(privateKey,
                                                                                                   publicKey,
                                                                                                   address))
        print("Your new address and private key are now in the file {0}".format(filename))
        print("copy this file to a secure directory, and delete your private key from the original")
    print(address)
    return address


sql_create_tasks_table = """CREATE TABLE IF NOT EXISTS blocks (
                                    id integer PRIMARY KEY, 
                                    num_block integer NOT NULL,
                                    hash text,
                                    transactions text,
                                    timestamp text,
                                    difficulty bigint, 
                                    previous_hash text not null,
                                    nonce bigint,
                                    reward float,
                                    gaslimit integer,
                                    gasused integer, 
                                    size integer,
                                    extra text,
                                    fees float
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
    fichier_db = r".\db\pythonsqlite.db"
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
