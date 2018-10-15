import pytest
import json

from web3 import Web3, EthereumTesterProvider
from web3.contract import ImplicitContract
from eth_utils import keccak, to_bytes
from model import ModelContract, Controller, Listener, calc_root, EMPTY_NODE_HASHES


web3 = Web3(EthereumTesterProvider())


@pytest.fixture
def accounts():
    return web3.eth.accounts


class TestContract:
    def __new__(cls, filename):
        with open(filename, 'r') as f:
            interface = json.loads(f.read())
        contract = web3.eth.contract(**interface)
        tx_hash = contract.constructor().transact()
        tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)
        instance = web3.eth.contract(address=tx_receipt.contractAddress, **interface)
        return ImplicitContract(instance)


@pytest.fixture(params=['model','../vyper.json','../solidity.json'])
def contract(request):
    filename = request.param
    if filename == 'model':
        return ModelContract()
    else:
        return TestContract(filename)


def test_root(accounts, contract):
    empty_value = contract.status(accounts[0])
    assert empty_value == 0
    root = calc_root(accounts[0], empty_value, EMPTY_NODE_HASHES)
    # Validate our calculated root produces the expected answer
    assert root == keccak(EMPTY_NODE_HASHES[0] + EMPTY_NODE_HASHES[0])
    # Validate our calculated root produces the same result as the contract's root
    assert root == contract.root()


def test_listener(accounts, contract):
    c = Controller(contract)
    values = []  # Test sequence
    # Set and reset
    values.append(1)
    # 2 sets in a row
    values.append(2)
    values.append(3)
    # Followed by a reset
    values.append(0)
    # Initialize our actor models
    l = Listener(accounts[0], contract)
    # Run the test sequence!
    for v in values:
        c.set(l.acct, v)
        assert c.get(l.acct) == l.status == v


def test_updates(accounts, contract):
    c = Controller(contract)
    listeners = [Listener(a, contract) for a in accounts]
    # Have a bunch of random assigments happen
    # See if one of them blows an assert when syncing
    for i in range(1, 11):
        for j, l in enumerate(listeners):
            value = i
            c.set(l.acct, value)
            assert c.get(l.acct) == l.status == value
