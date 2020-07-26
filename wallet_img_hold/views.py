import datetime
import json
import sqlite3
from sqlite3 import Error
from .wallet import Wallet
from wallet_img_hold import app
from flask import Flask, redirect, render_template, request
import requests


# The node with which our application interacts, there can be multiple
# such nodes as well.


CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

posts = []


my_wallet = Wallet('')

"""
https://swcarpentry.github.io/sql-novice-survey/10-prog/index.html
https://github.com/sqlcipher/sqlcipher
il faut stocker les adresses de wallet public qui font des demandes pour la vérification des tokens détenu en cas de data "payante"
pour la première demande d'une adresse inconnu, vérifier si l'adresse du wallet existe dans la blockchain
ajouter la possibilité d'uploader sur un autre wallet
faire une transaction pour des demandes d'images 'payantes'
ajouter des images pour créer un bloc dans la chain
créer une socket qui se connecte au serveur pour dire que ce wallet héberge des images
"""

def create_database(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()


def fetch_posts():
    """
    Function to fetch the chain from a blockchain node, parse the
    data and store it locally.
    """
    get_chain_address = "{}/chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        content = []
        chain = json.loads(response.content)
        for block in chain["chain"]:
            for tx in block["transactions"]:
                tx["index"] = block["index"]
                tx["hash"] = block["previous_hash"]
                content.append(tx)

        global posts
        posts = sorted(content, key=lambda k: k['timestamp'],
                       reverse=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/connect', methods=['POST'])
def connect():
    public_addr = request.form["public"]
    private_key = request.form["private"]
    my_wallet = Wallet("51.15.157.164", public_addr, private_key)

    if my_wallet.connect_wallet():
        my_wallet.check_transactions()
        return redirect('/my_wallet')

@app.route('/create_wallet')
def createaccount():
    my_wallet.create_new_wallet()
    return redirect('/')

@app.route('/my_wallet')
def get_my_wallet():
    return render_template('wallet.html', my_public_address=my_wallet.getPublicKey(), my_amount=my_wallet.getAmount())

@app.route('/send', methods=['POST'])
def send():
    addr = request.form["addr"]
    amount = request.form["amount"]
    sending = my_wallet.send_transaction(addr, amount)
    if sending:
        return redirect('/my_wallet')
    else:
        return redirect('/error')

#@app.route('/post_manga', method=['POST'])

#@app.route('/get_manga', method=['POST'])

def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')

