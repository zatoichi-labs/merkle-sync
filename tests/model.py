from eth_utils import keccak, to_bytes
from sparse_merkle_tree import SparseMerkleTree, EMPTY_NODE_HASHES, TREE_HEIGHT


def calc_root(key: bytes, value: bytes, branch: list):
    parent_hash = keccak(value)
    path = int.from_bytes(key, byteorder='big')
    target_bit = 1
    
    # Bottom up
    for sibling in reversed(branch):
        # Only update the proof for the part
        # of the path that matches
        if path & target_bit:
            # branch is in top down order
            # (key is in MSB to LSB order)
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

    def set(self, key: bytes, value: bytes, proof: list):
        # Validate proper input
        branch = self._smt.branch(key)
        assert branch == proof
        # Now set value
        self._smt.set(key, value)
        # Log the update with the branch for it
        proof_updates = self._smt.branch(key)
        self._logs.append((key, value, proof_updates))
    
    def status(self, key: bytes):
        return self._smt.get(key)

    @property
    def logs(self):
        return self._logs

class Controller:
    """
    The Controller has the full smt and can set any key
    """
    def __init__(self, tree):
        self.tree = tree

    def branch(self, key: bytes):
        return self.tree._smt.branch(key)

    def set(self, key: bytes, value: bytes):
        self.tree.set(key, value, self.branch(key))
    
    def get(self, key: bytes):
        return self.tree.status(key)


class Listener:
    """
    The Listener listens for updates and synchronizes their
    proof and value accordingly
    """
    def __init__(self, acct, tree):
        self.tree = tree
        self.acct = acct
        self._value = b''
        self.proof = EMPTY_NODE_HASHES
        self.last_synced = 0

    def update_proof(self, log):
        # When a new log is added, process it
        (key, value, proof) = log
        # Path diff is the logical XOR of the updated key and this account
        path_diff = (int.from_bytes(key, byteorder='big') ^ \
                int.from_bytes(self.acct, byteorder='big'))
        # Loop through the path updates from root to leaf
        for n in reversed(range(TREE_HEIGHT)):
            # Only update the proof for the part
            # of the path that matches
            if (path_diff & (1 << n)):
                break  # Indicates different branch than ours, so exit
            # proof is in top down order
            # (key is in MSB to LSB order)
            i = TREE_HEIGHT - 1 - n  # Flip accessor
            self.proof[i] = proof[i]  # Update matching node in path
        
        # Full match to key (no diff), update our tracked value
        # NOTE: Could probably just replace proof instead of looping,
        #       but this is not the common use case
        if path_diff == 0:
            print('Updating value from', '0x'+self._value.hex(), 'to', '0x'+value.hex())
            self._value = value

    def sync(self):
        # Iterate over last unchecked logs, update proof for them
        for log in self.tree.logs[self.last_synced:]:
            self.update_proof(log)
        # Remember to cache the last index synced
        self.last_synced = len(self.tree.logs)
    
    @property
    def value(self):
        # Validate that the value is up-to-date
        self.sync()
        # Validate that the proof is correct (and therefore matches tree)
        root = calc_root(self.acct, self._value, self.proof)
        assert root == self.tree.root()
        # NOTE: Sanity check that values line up
        assert self.tree.status(self.acct) == self._value
        return self._value
