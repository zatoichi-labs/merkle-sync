# Event to synchronize with tree updates
UpdatedBranch: event({
        key: indexed(bytes32),
        value: indexed(bytes32),
        updates: bytes32[160]  # Hash updates for key, starting with root
    })


# Root of the tree. Used to validate state transitions
root: public(bytes32)  # Must be initialized for an empty tree

# "key" denotes path from root to leaf (1 is right, 0 is left)
db: bytes32[bytes32]  # Key: Value DB (empty to start)


@public
def __init__():
    empty_node: bytes32 = keccak256(convert(0, 'bytes32'))  # Empty bytes32
    # Compute and set empty root hash
    for lvl in range(160):
        empty_node = keccak256(concat(empty_node, empty_node))
    self.root = empty_node


@private
def _set(_key: bytes32, _value: bytes32, _proof: bytes32[160]):
    #  Start at the leaf
    new_node_hash: bytes32 = keccak256(_value)
    old_node_hash: bytes32 = keccak256(self.db[_key])
    
    # For recording the updated proof as we go (root->leaf order)
    proof_updates: bytes32[160]
    proof_updates[159] = new_node_hash
    
    # Validate each step of the proof is correct, traversing from leaf->root
    # Also, keep track of the merklized updates
    for i in range(159): # 0 to 160-1, start at end of proof and travel upwards
        lvl: int128 = 160-1 - i  # 159 to 1 (159 - [0:158] = [159:1])

        # Keypath is in MSB to LSB order (for root->leaf order), so traverse backwards:
        # (leaf is bit 0, root is bit 160)
        # Path traversal right is whether key has bit at `lvl` set
        if bitwise_and(convert(_key, 'uint256'), shift(1, i)):
            # Path goes to right, so sibling is left
            # Show hash of prior update and sibling matches next level up
            assert _proof[lvl-1] == keccak256(concat(_proof[lvl], old_node_hash))
            # Record update of hashing prior update and sibling
            proof_updates[lvl-1] = keccak256(concat(_proof[lvl], new_node_hash))
        else:
            # Path goes to left, so sibling is right
            # Show hash of prior update and sibling matches next level up
            assert _proof[lvl-1] == keccak256(concat(old_node_hash, _proof[lvl]))
            # Record update of hashing prior update and sibling
            proof_updates[lvl-1] = keccak256(concat(new_node_hash, _proof[lvl]))

        # Update loop variables
        old_node_hash = _proof[lvl]
        new_node_hash = proof_updates[lvl]
    
    # Validate and update root hash using the same methodology
    if bitwise_and(convert(_key, 'uint256'), shift(1, 159)):
        # Path goes to right, so sibling is left
        # Show hash of prior update and sibling matches stored root
        assert self.root == keccak256(concat(_proof[0], old_node_hash))
        # Update stored root to computed root update (for updated value)
        self.root = keccak256(concat(_proof[0], new_node_hash))
    else:
        # Path goes to left, so sibling is right
        # Show hash of prior update and sibling matches stored root
        assert self.root == keccak256(concat(old_node_hash, _proof[0]))
        # Update stored root to computed root update (for updated value)
        self.root = keccak256(concat(new_node_hash, _proof[0]))

    # Finally update value in db since we validated the proof
    self.db[_key] = _value

    # Tell the others about the update!
    log.UpdatedBranch(_key, _value, proof_updates)


# Update these functions for whatever use case you have here
@public
def set(_acct: address, _value: uint256, _proof: bytes32[160]):
    self._set(convert(_acct, 'bytes32'), convert(_value, 'bytes32'), _proof)


@public
@constant
def status(_acct: address) -> uint256:
    return convert(self.db[convert(_acct, 'bytes32')], 'uint256')
