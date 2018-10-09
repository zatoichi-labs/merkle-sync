from eth_utils import keccak, to_int

from web3 import Web3
sha3 = Web3.soliditySha3


class ValidationError(Exception):
    pass


TREE_HEIGHT=160
EMPTY_VALUE=b'\x00' * 32
# keccak(EMPTY_VALUE)
EMPTY_LEAF_NODE_HASH = b')\r\xec\xd9T\x8bb\xa8\xd6\x03E\xa9\x888o\xc8K\xa6\xbc\x95H@\x08\xf66/\x93\x16\x0e\xf3\xe5c'


# sanity check
assert EMPTY_LEAF_NODE_HASH == sha3(['bytes32'], [EMPTY_VALUE])
EMPTY_NODE_HASHES = [EMPTY_LEAF_NODE_HASH]


hash_duplicate = lambda h: sha3(['bytes32', 'bytes32'], [h, h])
for _ in range(TREE_HEIGHT-1):
    EMPTY_NODE_HASHES.insert(0, hash_duplicate(EMPTY_NODE_HASHES[0]))


def validate_is_bytes(value):
    if not isinstance(value, bytes):
        raise ValidationError("Value is not of type `bytes`: got '{0}'".format(type(value)))


def validate_length(value, length):
    if len(value) != length:
        raise ValidationError("Value is of length {0}.  Must be {1}".format(len(value), length))


class SparseMerkleTree:
    def __init__(self, db={}):
        self.db = db
        # Initialize an empty tree with one branch
        self.root_hash = hash_duplicate(EMPTY_NODE_HASHES[0])
        self.db[self.root_hash] = EMPTY_NODE_HASHES[0] + EMPTY_NODE_HASHES[0]
        for i in range(TREE_HEIGHT - 1):
            self.db[EMPTY_NODE_HASHES[i]] = EMPTY_NODE_HASHES[i+1] + EMPTY_NODE_HASHES[i+1]
        self.db[EMPTY_LEAF_NODE_HASH] = EMPTY_VALUE

    def get(self, key):
        value, _ = self._get(key)
        return value
    
    def branch(self, key):
        _, branch = self._get(key)
        return branch

    def _get(self, key):
        validate_is_bytes(key)
        validate_length(key, 20)
        branch = []

        target_bit = 1 << TREE_HEIGHT - 1
        path = to_int(key)
        node_hash = self.root_hash
        # Append the sibling to the branch
        # Iterate on the parent
        for i in range(TREE_HEIGHT):
            if path & target_bit:
                branch.append(self.db[node_hash][:32])
                node_hash = self.db[node_hash][32:]
            else:
                branch.append(self.db[node_hash][32:])
                node_hash = self.db[node_hash][:32]
            target_bit >>= 1

        return self.db[node_hash], branch

    def set(self, key, value):
        validate_is_bytes(key)
        validate_length(key, 20)
        validate_is_bytes(value)

        path = to_int(key)
        self.root_hash = self._set(value, path, 0, self.root_hash)

    def _set(self, value, path, depth, node_hash):
        if depth == TREE_HEIGHT:
            return self._hash_and_save(value)
        else:
            node = self.db[node_hash]
            target_bit = 1 << (TREE_HEIGHT - depth - 1)
            if (path & target_bit):
                return self._hash_and_save(node[:32] + self._set(value, path, depth+1, node[32:]))
            else:
                return self._hash_and_save(self._set(value, path, depth+1, node[:32]) + node[32:])

    def exists(self, key):
        validate_is_bytes(key)
        validate_length(key, 20)
        return (self.get(key) != EMPTY_VALUE)

    def delete(self, key):
        """
        Equals to setting the value to None
        """
        validate_is_bytes(key)
        validate_length(key, 20)

        self.set(key, EMPTY_VALUE)

    #
    # Utils
    #
    def _hash_and_save(self, node):
        """
        Saves a node into the database and returns its hash
        """

        node_hash = keccak(node)
        self.db[node_hash] = node
        return node_hash

    #
    # Dictionary API
    #
    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __delitem__(self, key):
        return self.delete(key)

    def __contains__(self, key):
        return self.exists(key)
