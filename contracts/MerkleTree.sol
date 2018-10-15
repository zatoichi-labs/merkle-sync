pragma solidity ^0.4.25;

contract MerkleTree {
    // Event to synchronize with tree updates
    event UpdatedBranch(
        bytes32 indexed key,
        bytes32 indexed value,
        bytes32[160] updates // Hash updates for key, starting with root
    );

    // Root of the tree. Used to validate state transitions
    bytes32 public root;

    // "key" denotes path from root to leaf (1 is right, 0 is left)
    mapping (bytes32 => bytes32) db;

    constructor() public {
        bytes32 empty_node = keccak256(abi.encodePacked(bytes32(0))); // Empty bytes32 value
        // Compute and set empty root hash
        for (uint i=0; i < 160; i++)
            empty_node = keccak256(abi.encodePacked(empty_node, empty_node));
        root = empty_node;
    }

    function _set(
        bytes32 _key,
        bytes32 _value,
        bytes32[160] _proof
    )
        private
    {
        // Start at the leaf
        bytes32 old_node_hash = keccak256(abi.encodePacked(db[_key]));

        // For recording the updated proof as we go (root->leaf order)
        bytes32[160] memory proof_updates;
        // Also start updates at leaf
        proof_updates[159] = keccak256(abi.encodePacked(_value));

        // Validate each step of the proof is correct, traversing from leaf->root
        // Also, keep track of the merklized updates
        for (uint lvl = 159; lvl > 0; lvl--) {
            // Keypath is in MSB to LSB order (for root->leaf order), so traverse backwards:
            // (leaf is bit 0, root is bit 160)
            // Path traversal right is whether key has bit at `lvl` set
            if ( (uint(_key) & 1 << (160-1-lvl)) > 0 ) {
                // Path goes to right, so sibling is left
                // Show hash of prior update and sibling matches next level up
                require(_proof[lvl-1] == keccak256(abi.encodePacked(_proof[lvl], old_node_hash)));
                // Record hash of node update and sibling
                proof_updates[lvl-1] = keccak256(abi.encodePacked(_proof[lvl], proof_updates[lvl]));
            } else {
                // Path goes to left, so sibling is right
                // Show hash of prior update and sibling matches next level up
                require(_proof[lvl-1] == keccak256(abi.encodePacked(old_node_hash, _proof[lvl])));
                // Record hash of node update and sibling
                proof_updates[lvl-1] = keccak256(abi.encodePacked(proof_updates[lvl], _proof[lvl]));
            }
            // Update loop variables
            old_node_hash = _proof[lvl];
        }
        
        // Validate and update root hash using the same methodology
        if ( (uint(_key) & 1 << (160-1)) > 0 ) {
            // Path goes to right, so sibling is left
            // Show hash of prior update and sibling matches stored root
            require(root == keccak256(abi.encodePacked(_proof[0], old_node_hash)));
            // Update stored root to computed root update (for updated value)
            root = keccak256(abi.encodePacked(_proof[0], proof_updates[0]));
        } else {
            // Path goes to left, so sibling is right
            // Show hash of prior update and sibling matches stored root
            require(root == keccak256(abi.encodePacked(old_node_hash, _proof[0])));
            // Update stored root to computed root update (for updated value)
            root = keccak256(abi.encodePacked(proof_updates[0], _proof[0]));
        }

        // Finally update value in db since we validated the proof
        db[_key] = _value;

        // Tell the others about the update!
        emit UpdatedBranch(_key, _value, proof_updates);
    }

    // Update these functions for whatever use case you have here
    function set(
        address _acct,
        uint256 _status,
        bytes32[160] _proof
    )
        public
    {
        _set(bytes32(_acct), bytes32(_status), _proof);
    }

    function status(address _acct)
        public
        view
        returns (uint256)
    {
        return uint256(db[bytes32(_acct)]);
    }
}
