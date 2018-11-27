import math
from eth_utils import keccak, to_bytes, to_int, to_checksum_address, to_canonical_address
from trie.smt import SparseMerkleTree, SparseMerkleProof, calc_root as bytes_calc_root


TREE_HEIGHT = 160
KEYSIZE = TREE_HEIGHT//8
DEFAULT = b'\x00' * 32


def int_to_bytes32(value: int) -> bytes:
    v = to_bytes(value).rjust(32, b'\x00')
    assert len(v) == 32, "Integer Overflow/Underflow"
    return v


def calc_root(key, value, branch):
    return bytes_calc_root(to_canonical_address(key), int_to_bytes32(value), branch)


class MerkleSyncTree(SparseMerkleTree):
    def __init__(self):
        super().__init__(keysize=KEYSIZE, default=DEFAULT)

    def get(self, key):
        return to_int(super().get(to_canonical_address(key)))

    def branch(self, key):
        return super().branch(to_canonical_address(key))

    def set(self, key, value):
        return super().set(to_canonical_address(key), int_to_bytes32(value))


_smt = MerkleSyncTree()
EMPTY_NODE_HASHES = _smt.branch('0x0000000000000000000000000000000000000000')[:]
del _smt

fmt = lambda h: h[:5] + '...' + h[-3:]
class MerkleSyncProof:
    def __init__(self, acct):
        self._proof = SparseMerkleProof(to_canonical_address(acct), DEFAULT, EMPTY_NODE_HASHES)

    @property
    def key(self):
        return to_checksum_address(self._proof.key)

    @property
    def value(self):
        return to_int(self._proof.value)

    @property
    def branch(self):
        return self._proof.branch

    @property
    def root_hash(self):
        return self._proof.root_hash

    def merge(self, key, value, node_updates):
        self._proof.merge(to_canonical_address(key), int_to_bytes32(value), node_updates)


class ModelContract:
    def __init__(self):
        self._smt = MerkleSyncTree()
        self._logs = []
    
    def root(self):
        return self._smt.root_hash

    def set(self, key: str, value: int, proof: list):
        # Validate proof works for key-value pair
        # NOTE: proof is in root->leaf order
        assert calc_root(key, self.status(key), proof) == self.root()

        # Now set value (root->leaf order)
        proof_updates = self._smt.set(key, value)

        # Log the update with the branch for it
        self._logs.append((key, value, proof_updates))
    
    def status(self, key: str) -> int:
        return self._smt.get(key)

    @property
    def logs(self):
        return self._logs


# TODO Add optimization that controller tracks key depth to reduce communication
class Controller:
    """
    The Controller has the full smt and can set any key
    """
    def __init__(self, tree):
        self.tree = tree
        self._smt = MerkleSyncTree()

    def set(self, key: str, value: int):
        # Branch is in leaf->root order
        self.tree.set(key, value, self._smt.branch(key))
        self._smt.set(key, value)
        assert self._smt.root_hash == self.tree.root()
    
    def get(self, key: str) -> int:
        assert self._smt.root_hash == self.tree.root()
        assert self.tree.status(key) == self._smt.get(key)
        return self._smt.get(key)


class Listener:
    """
    The Listener listens for updates and synchronizes their
    proof and value accordingly
    """
    def __init__(self, acct, tree):
        self._tree = tree
        self.acct = acct
        self._proof = MerkleSyncProof(acct)
        self._last_synced = 0

    def sync(self):
        # Iterate over last unchecked logs, update proof for them
        for key, value, node_updates in self._tree.logs[self._last_synced:]:
            self._proof.merge(key, value, node_updates)

        # Remember to cache the last index synced
        self._last_synced = len(self._tree.logs)
    
    @property
    def status(self):
        # Validate that the value is up-to-date
        self.sync()
        # NOTE: Sanity check that values line up
        assert self._tree.status(self._proof.key) == self._proof.value
        # Validate that the proof is correct (and therefore matches tree)
        assert self._proof.root_hash == self._tree.root()
        return self._proof.value
