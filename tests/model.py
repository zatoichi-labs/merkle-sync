import math
from eth_utils import keccak, to_bytes, to_int
from sparse_merkle_tree import SparseMerkleTree, EMPTY_NODE_HASHES, TREE_HEIGHT


def to_bytes32(value: int) -> bytes:
    v = to_bytes(value).rjust(32, b'\x00')
    assert len(v) == 32, "Integer Overflow/Underflow"
    return v


def calc_root(key: str, value: int, branch: list):
    parent_hash = keccak(to_bytes32(value))
    path = int(key, 16)
    
    # traverse the path in leaf->root order
    # branch is in root->leaf order (key is in MSB to LSB order)
    target_bit = 1
    for sibling in reversed(branch):
        if path & target_bit:
            parent_hash = keccak(sibling + parent_hash)
        else:
            parent_hash = keccak(parent_hash + sibling)
        target_bit <<= 1
    
    return parent_hash


class ModelContract:
    def __init__(self):
        self._smt = SparseMerkleTree({})
        self._logs = []
    
    def root(self):
        return self._smt.root_hash

    def set(self, key: str, value: int, proof: list):
        # Validate proof works for key-value pair
        # NOTE: proof is in root->leaf order
        assert calc_root(key, value, proof) == self.root()

        # Now set value (root->leaf order)
        proof_updates = self._smt.set(to_bytes(hexstr=key), to_bytes32(value))

        # Log the update with the branch for it
        self._logs.append((key, value, proof_updates))
    
    def status(self, key: str) -> int:
        return to_int(self._smt.get(to_bytes(hexstr=key)))

    @property
    def logs(self):
        return self._logs


class Controller:
    """
    The Controller has the full smt and can set any key
    """
    def __init__(self, tree):
        self.tree = tree
        self._smt = SparseMerkleTree({})

    def branch(self, key: str):
        # root->leaf order
        return self._smt.branch(to_bytes(hexstr=key))

    def set(self, key: str, value: int):
        # Branch is in leaf->root order
        self.tree.set(key, value, self.branch(key))
        self._smt.set(to_bytes(hexstr=key), to_bytes32(value))
    
    def get(self, key: str) -> int:
        assert self.tree.status(key) == \
                int.from_bytes(self._smt.get(to_bytes(hexstr=key)), byteorder='big')
        return self.tree.status(key)


class Listener:
    """
    The Listener listens for updates and synchronizes their
    proof and value accordingly
    """
    def __init__(self, acct, tree):
        self._tree = tree
        self._key = acct
        self._value = 0
        self._proof = EMPTY_NODE_HASHES  # root->leaf order
        self._last_synced = 0

    @property
    def acct(self):
        return self._key

    def update_proof(self, log):
        # When a new log is added, process it
        # proof updates are in root->leaf order already
        (key, value, path_updates) = log

        # Path diff is the logical XOR of the updated key and this account
        path_diff = (int(key, 16) ^ int(self._key, 16))

        # Full match to key (no diff), update our tracked value
        # NOTE: No need to update the proof
        if path_diff == 0:
            self._value = value
        else:
            # Find the first non-zero entry
            # (place where branch happens between keypaths)
            i = int(math.log(path_diff, 2))

            # Update sibling in proof where we branch off from the update
            # NOTE: Proof updates are provided in reverse order from proof
            self._proof[i] = path_updates[i]

    def sync(self):
        # Iterate over last unchecked logs, update proof for them
        for log in self._tree.logs[self._last_synced:]:
            self.update_proof(log)

        # Remember to cache the last index synced
        self._last_synced = len(self._tree.logs)
    
    @property
    def status(self):
        # Validate that the value is up-to-date
        self.sync()

        # NOTE: Sanity check that values line up
        assert self._tree.status(self._key) == self._value

        # Validate that the proof is correct (and therefore matches tree)
        assert calc_root(self._key, self._value, self._proof) == self._tree.root()
        return self._value
