import sys
from block import Block
import time
from transaction import Vout, Transaction
import sqlite3
import json

class Blockchain:
    difficulty = 1

    def __init__(self, address_wallet_miner, fichier_db): #= r".\db\pythonsqlite2.db"
        self.unconfirmed_transactions = {}
        self.unconfirmed_transactions
        self.address_wallet_miner = address_wallet_miner
        self.chain = []
        self.conn = sqlite3.connect(fichier_db, check_same_thread=False, isolation_level=None)
        self.miningJob = False

    def create_genesis_block(self):
        genesis_block = Block(0, "", "", 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.conn.execute('''
                INSERT INTO blocks (num_block,hash,transactions,timestamp, previous_hash,nonce)
                        VALUES(?,?,?,?,?,?)
                          ''', (
        genesis_block.index, genesis_block.hash, json.dumps(genesis_block.transactions), genesis_block.timestamp, genesis_block.previous_hash, genesis_block.nonce))
        #self.chain.append(genesis_block)

    @property
    def get_last_block(self):
        myBlock = self.conn.execute('''SELECT * FROM blocks ORDER BY id DESC LIMIT 1''').fetchone()
        if myBlock:
            return Block(myBlock[1], myBlock[3], myBlock[4], myBlock[5], myBlock[2], myBlock[6])
        else:
            return None

    def add_block(self, block, proof):
        previous_hash = self.get_last_block.hash
        if previous_hash != block.previous_hash:
            print('previous hash faux')
            return False

        if not Blockchain.is_valid_proof(block, proof):
            print('block non valide')
            return False

        block.hash = proof

        self.conn.execute('''
                    INSERT INTO blocks (num_block,hash,transactions,timestamp, previous_hash,nonce)
                            VALUES(?,?,?,?,?,?)
                              ''', (
        block.index, block.hash, json.dumps(block.transactions), block.timestamp, block.previous_hash, block.nonce))
        return True

    @staticmethod
    def proof_of_work(block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_transaction(self, transaction):
        if not self.unconfirmed_transactions:
            self.unconfirmed_transactions['data'] = []
            self.unconfirmed_transactions['transac'] = []
        if 'data' in transaction:
            self.unconfirmed_transactions['data'].append(transaction['data'])
        if 'transac' in transaction:
            for transacLine in transaction['transac']:
                transacVout = Vout(transacLine['to'],transacLine['from'], transacLine['amount'], transacLine['signature'], transacLine['message'], transacLine['timestamp']).__dict__
                transacTemp = {}
                transacTemp['transac'] = Transaction([], transacVout).__dict__
                #transacTemp['transac'].transfer(transacLine['from'], transacLine['to'], transacLine['amount'])
                self.unconfirmed_transactions['transac'].append(dict(transacTemp['transac']))
        if 'miningReward' in transaction:
            self.unconfirmed_transactions['transac'].append(dict(transaction['miningReward']))

        if self.get_size(self.unconfirmed_transactions) >= 15000 and not self.miningJob:
            self.miningJob = True
            return True
        else:
            return None

    def get_size(self, obj, seen=None):
        """Recursively finds size of objects"""
        size = sys.getsizeof(obj)
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        # Important mark as seen *before* entering recursion to gracefully handle
        # self-referential objects
        seen.add(obj_id)
        if isinstance(obj, dict):
            size += sum([self.get_size(v, seen) for v in obj.values()])
            size += sum([self.get_size(k, seen) for k in obj.keys()])
        elif hasattr(obj, '__dict__'):
            size += self.get_size(obj.__dict__, seen)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
            size += sum([self.get_size(i, seen) for i in obj])
        return size

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):

        if not self.unconfirmed_transactions:
            return False

        last_block = self.get_last_block
        rewardT = Vout(self.address_wallet_miner, "", 20, "", "", time.time()).__dict__
        reward = {}
        reward['miningReward'] = Transaction([], rewardT).__dict__
        self.add_new_transaction(reward)
        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=str(time.time()),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        self.unconfirmed_transactions = {}
        self.miningJob = False

        return True

    def get_block_by_index(self, index):
        myBlock = self.conn.execute('''SELECT * FROM blocks WHERE num_block=?''', (index,)).fetchone()
        if myBlock:
            return Block(myBlock[1], myBlock[3], myBlock[4], myBlock[5], myBlock[2], myBlock[6]).__dict__
        else:
            return 'None'

    def find_block_by_hash(self, hash):
        myBlock = self.conn.execute('''SELECT * FROM blocks WHERE hash=?''', (hash,)).fetchone()
        return Block(myBlock[1], myBlock[3], myBlock[4], myBlock[5], myBlock[2], myBlock[6]).__dict__

    def get_chain(self):
        list_block = []
        myBlock = self.conn.execute('''SELECT * FROM blocks''').fetchall()
        for block in myBlock:
            list_block.append(Block(block[1], block[3], block[4], block[5], block[2], block[6]).__dict__)
        return list_block
