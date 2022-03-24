# coding:utf-8
import time
import json
import hashlib


class Vin():
    def __init__(self, utxo_hash, amount):
        self.hash = utxo_hash
        self.amount = amount
        # self.unLockSig = unLockSig


class Vout():
    def __init__(self, receiver, sender, amount, signature, message, timestamp):
        self.receiver = receiver
        self.sender = sender
        self.amount = amount
        self.signature = signature
        self.message = message
        self.timestamp = timestamp
        self.hash = hashlib.sha256(
            (str(time.time()) + str(self.receiver) + str(self.sender) + str(self.message) + str(self.signature) + str(self.amount)).encode('utf-8')).hexdigest()
        # self.lockSig = lockSig

    @classmethod
    def get_unspent(cls, addr):
        """
        Exclude all consumed VOUT, get unconsumed VOUT
        """
        unspent = []
        all_tx = []
        spend_vin = []
        [spend_vin.extend(item['vin']) for item in all_tx]
        has_spend_hash = [vin['hash'] for vin in spend_vin]
        for item in all_tx:
            # Vout receiver is addr and the vout hasn't spent yet.
            for vout in item['vout']:
                if vout['receiver'] == addr and vout['hash'] not in has_spend_hash:
                    unspent.append(vout)
        return [Vin(tx['hash'], tx['amount']) for tx in unspent]


class Transaction():
    def __init__(self, vin, vout, ):
        self.timestamp = int(time.time())
        self.vin = vin
        self.vout = vout
        self.hash = self.gen_hash()

    def gen_hash(self):
        return hashlib.sha256((str(self.timestamp) + str(self.vin) + str(self.vout)).encode('utf-8')).hexdigest()

    @classmethod
    def transfer(cls, from_addr, to_addr, amount):
        if not isinstance(amount, int):
            amount = int(amount)
        unspents = Vout.get_unspent(from_addr)
        ready_utxo, change = select_outputs_greedy(unspents, amount)
        vin = ready_utxo
        vout = []
        vout.append(Vout(to_addr, amount))
        vout.append(Vout(from_addr, change))
        tx = cls(vin, vout)
        tx_dict = tx.to_dict()
        #UnTransactionDB().insert(tx_dict)
        return tx_dict

    def to_dict(self):
        dt = self.__dict__
        if not isinstance(self.vin, list):
            self.vin = [self.vin]
        if not isinstance(self.vout, list):
            self.vout = [self.vout]
        dt['vin'] = [i.__dict__ for i in self.vin]
        dt['vout'] = [i.__dict__ for i in self.vout]
        return dt


def select_outputs_greedy(unspent, min_value):
    if not unspent: return None
    lessers = [utxo for utxo in unspent if utxo.amount < min_value]
    greaters = [utxo for utxo in unspent if utxo.amount >= min_value]
    key_func = lambda utxo: utxo.amount
    greaters.sort(key=key_func)
    if greaters:
        min_greater = greaters[0]
        change = min_greater.amount - min_value
        return [min_greater], change
    lessers.sort(key=key_func, reverse=True)
    result = []
    accum = 0
    for utxo in lessers:
        result.append(utxo)
        accum += utxo.amount
        if accum >= min_value:
            change = accum - min_value
            return result, change
    return None, 0