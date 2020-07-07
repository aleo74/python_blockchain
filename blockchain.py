from block import Block
import time
from transaction import Vout, Transaction


class Blockchain:
    difficulty = 1

    def __init__(self, address_wallet_miner):
        self.unconfirmed_transactions = {}
        self.unconfirmed_transactions
        self.address_wallet_miner = address_wallet_miner
        self.chain = []

    def create_genesis_block(self):
        genesis_block = Block(0, self.address_wallet_miner, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def get_last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        previous_hash = self.get_last_block.hash
        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
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
            self.unconfirmed_transactions['data'].append(dict(transaction['data']))
        if 'transac' in transaction:
            print(transaction)
            self.unconfirmed_transactions['transac'].append(dict(transaction['transac']))

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
        rewardT = Vout(self.address_wallet_miner, 20).__dict__
        reward = {}
        reward['transac'] = Transaction([], rewardT).__dict__
        self.add_new_transaction(reward)
        print(self.unconfirmed_transactions)
        new_block = Block(index=last_block.index + 1,
                          miner=self.address_wallet_miner,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []

        return True

    def get_block_by_index(self, index):
        return self.chain[index].__dict__

    def find_block_by_hash(self, hash):
        for block in self.chain:
            if block.hash == hash:
                return block.__dict__