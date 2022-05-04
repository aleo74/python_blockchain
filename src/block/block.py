# coding: utf-8
import json
from hashlib import sha256


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, difficulty, hash="", nonce=0, reward=0,
                 gaslimit=80000000, gasused=0, size=0, extra='', fees=0.0):
        self.index = int(index)
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.hash = hash
        self.difficulty = difficulty
        self.nonce = int(nonce)
        self.reward = reward
        self.gaslimit = gaslimit
        self.gasused = gasused
        self.size = size
        self.extra = extra
        self.fees = fees

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    def get_block_string(self):
        return json.dumps(self.__dict__, sort_keys=True)