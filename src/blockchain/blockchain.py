import sys
from block.block import Block
import time
from transaction_chain.transaction import Vout, Transaction
import sqlite3
import json


class Blockchain:
    difficulty = 1

    def __init__(self, address_wallet_miner, fichier_db, difficulty=1):
        self.unconfirmed_transactions = {}
        self.address_wallet_miner = address_wallet_miner
        self.chain = []
        self.last_id_block = 0
        self.conn = sqlite3.connect(fichier_db, check_same_thread=False, isolation_level=None)
        self.fichier = fichier_db
        self.miningJob = False
        self.difficulty = difficulty

    def create_genesis_block(self):
        genesis_block = Block(index=0, hash="", transactions="", timestamp="", previous_hash="0", difficulty=self.difficulty,
                              nonce=0, reward=0, gaslimit=80000000, gasused=0, size=0, extra='')
        genesis_block.size = self.get_size(genesis_block)
        genesis_block.reward = 100.0

        genesis_block.hash = self.proof_of_work(genesis_block)
        self.conn.execute('''
                INSERT INTO blocks (num_block,hash,transactions,timestamp, previous_hash,nonce, difficulty, reward,
                gaslimit, gasused, size, extra, fees)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                          ''', (
            genesis_block.index,
            genesis_block.hash,
            json.dumps(genesis_block.transactions),
            genesis_block.timestamp,
            genesis_block.previous_hash,
            genesis_block.nonce,
            genesis_block.difficulty,
            genesis_block.reward,
            genesis_block.gaslimit,
            genesis_block.gasused,
            genesis_block.size,
            genesis_block.extra,
            genesis_block.fees,)
                          )

    @property
    def get_last_block(self):
        block = self.conn.execute('''SELECT * FROM blocks ORDER BY id DESC LIMIT 1''').fetchone()
        if block:
            return Block(index=block[1], hash=block[2], transactions=block[3], timestamp=block[4], difficulty=block[5],
                      previous_hash=block[6], nonce=block[7], reward=block[8], gaslimit=block[9], gasused=block[10],
                      size=block[11], extra=block[12], fees=block[13])
        else:
            return None

    def add_block(self, block, hash_received):
        if len(block.previous_hash) > 1:
            previous_hash = self.get_last_block.hash
            if previous_hash != block.previous_hash:
                print('hash faux')
                return False
        if not Blockchain.is_valid_proof(block, hash_received):
            print('proof faux')
            return False
        block.hash = hash_received
        self.conn.execute('''
                    INSERT INTO blocks (num_block,hash,transactions,timestamp, previous_hash,nonce, difficulty, reward,
                    gaslimit, gasused, size, extra, fees)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                              ''', (
                    block.index,
                    block.hash,
                    json.dumps(block.transactions),
                    block.timestamp,
                    block.previous_hash,
                    block.nonce,
                    block.difficulty,
                    block.reward,
                    block.gaslimit,
                    block.gasused,
                    block.size,
                    block.extra,
                    block.fees,)
                      )
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
                if float(transacLine['amount']) > 0:
                    transacVout = Vout(transacLine['to'], transacLine['from'], transacLine['amount'],
                                       transacLine['signature'], transacLine['message'],
                                       transacLine['timestamp']).__dict__
                    transacTemp = {}
                    transacTemp['transac'] = Transaction([], transacVout).__dict__
                self.unconfirmed_transactions['transac'].append(dict(transacTemp['transac']))
        if 'miningReward' in transaction:
            self.unconfirmed_transactions['transac'].append(dict(transaction['miningReward']))

        if self.get_size(self.unconfirmed_transactions) >= 1000 and not self.miningJob:
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
    def is_valid_proof(cls, block, hash_received):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (hash_received.startswith('0' * block.difficulty) and
                hash_received == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
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
        rewardT = Vout(self.address_wallet_miner, "", self.rewardCalcul(), "", "", time.time()).__dict__
        reward = {}
        reward['miningReward'] = Transaction([], rewardT).__dict__
        self.add_new_transaction(reward)
        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=str(time.time()),
                          previous_hash=last_block.hash,
                          difficulty=1,
                          reward=float(self.rewardCalcul()),
                          extra='',
                          fees=float(self.calcul_fees()))
        new_block.size = self.get_size(new_block)
        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        self.unconfirmed_transactions = {}
        self.miningJob = False
        return True

    def rewardCalcul(self):
        len_chain = self.get_len_chain()
        max_reward = 100
        div = 1
        amount = 0
        while (200000 * div) <= len_chain:
            max_reward = max_reward / 2
            amount = amount + (200000 * max_reward)
            div = div + 1
        return max_reward

    def calcul_fees(self):
        return 0

    def get_block_by_index(self, index):
        block = self.conn.execute('''SELECT * FROM blocks WHERE num_block=?''', (index,)).fetchone()
        if block:
            return Block(index=block[1], hash=block[2], transactions=block[3], timestamp=block[4], difficulty=block[5],
                      previous_hash=block[6], nonce=block[7], reward=block[8], gaslimit=block[9], gasused=block[10],
                      size=block[11], extra=block[12], fees=block[13]).__dict__
        else:
            return 'None'

    def find_block_by_hash(self, hash):
        block = self.conn.execute('''SELECT * FROM blocks WHERE hash=?''', (hash,)).fetchone()
        return Block(index=block[1], hash=block[2], transactions=block[3], timestamp=block[4], difficulty=block[5],
                      previous_hash=block[6], nonce=block[7], reward=block[8], gaslimit=block[9], gasused=block[10],
                      size=block[11], extra=block[12], fees=block[13]).__dict__

    def get_chain(self):
        list_block = []
        myBlock = self.conn.execute('''SELECT * FROM blocks''').fetchall()
        for block in myBlock:
            list_block.append(
                Block(index=block[1], hash=block[2], transactions=block[3], timestamp=block[4], difficulty=block[5],
                      previous_hash=block[6], nonce=block[7], reward=block[8], gaslimit=block[9], gasused=block[10],
                      size=block[11], extra=block[12], fees=block[13]).__dict__)
        return list_block

    def get_len_chain(self):
        return self.conn.execute('''SELECT MAX(id) FROM blocks''').fetchone()[0]
