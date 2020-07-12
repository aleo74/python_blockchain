# python_blockchain

A simple blockchain from scratch in Python.

## How its work ?

I use a simple socket server to run the programs.


```sh
$git clone https://github.com/aleo74/python_blockchain.git
```

Start the first node with :
```sh
py server.py
```

The first node is running at localhost:1111

Run client on a different terminal session:
```sh
py client.py
```

Get the genesis block (on client) :
```sh
>> {"action": "get_chain"}
```

Add a new transaction (on client):
```sh
>> {"action": "new_transaction", "data": [{"author": "Aleo74", "content": "Your stuff"}]}
```

See pending transaction (on client):
```sh
>> {"action": "pending_tx"}
```

Mine it ! (on client):
```sh
>> {"action": "mine"}
```

## How to add a new node ?

Change the value of port
Start a new console :
```sh
py server.py
```

Use this command :
```sh
register_to_network
```

And you will see :
```sh
Registration on the network successful
```

The new server is now connected to the node !