# coding: utf-8

class Peer:
    def __init__(self):
        self.peers = []

    def add_peer(self, peer):
        self.peers.append(peer)

    def get_peers(self):
        return self.peers

    def unset_peer(self, peer):
        self.peers.remove(peer)

