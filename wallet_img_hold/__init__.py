from flask import Flask
from .wallet import Wallet
app = Flask(__name__)
from wallet_img_hold import views