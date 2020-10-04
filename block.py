# coding: utf-8
import json
from hashlib import sha256
import re

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, hash="", nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.hash = hash
        self.nonce = nonce

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        """

        block_string = json.dumps(self.__dict__, sort_keys=True)

        print('-------Block in string to hash-------')
        print(block_string)
        print('-------/Block in string to hash-------')
        return sha256(block_string.encode()).hexdigest()