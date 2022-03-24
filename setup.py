from setuptools import setup

setup(
    name='test',
    version='0.0.0.3ct',
    description='Revoir le consensus'
                'Ajouter un tableau pour les pending block'
                'Ajouter la possibilitee de miner des blocks en pending avec un mineur distant',
    author='',
    package_dir={'': 'src'},
    packages=[
        "block",
        "blockchain",
        "myPeer",
        "client",
        "server",
        "socket_server",
        "transaction_chain",
    ],
    entry_points={
        'console_scripts': [
            'start = server.main:main',
            'restart = server.main:restart',
            'join = server.main:join',
        ]
    }
)