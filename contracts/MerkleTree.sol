pragma solidity ^0.4.25;

contract MerkleTree {
    event UpdatedBranch(
        bytes32 indexed key,
        bytes32 indexed value,
        bytes32[160] branch
    );

    bytes32 public root;

    mapping (bytes32 => bytes32) db;

    constructor() public {
        bytes32 empty_node = keccak256(abi.encodePacked(bytes32(0))); // Empty bytes32 value
        // Compute empty root hash
        for (uint i=0; i < 160; i++)
            empty_node = keccak256(abi.encodePacked(empty_node, empty_node));
        // Set empty root hash
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
        bytes32 new_node_hash = keccak256(abi.encodePacked(_value));
        bytes32 prior_node_hash = keccak256(abi.encodePacked(db[_key]));

        // Record the updated proof as we go
        bytes32[160] memory proof_updates;
        proof_updates[159] = new_node_hash;

        for (uint lvl = 159; lvl > 0; lvl--) {
            // Path right is whether key has bit at `lvl` set
            if (_key & bytes32(2**(160-lvl)) > 0) {
                require(_proof[lvl-1] == keccak256(abi.encodePacked(_proof[lvl], prior_node_hash)));
                proof_updates[lvl-1] = keccak256(abi.encodePacked(_proof[lvl], new_node_hash));
            } else {
                require(_proof[lvl-1] == keccak256(abi.encodePacked(prior_node_hash, _proof[lvl])));
                proof_updates[lvl-1] = keccak256(abi.encodePacked(new_node_hash, _proof[lvl]));
            }
            // Update loop variables
            prior_node_hash = _proof[lvl];
            new_node_hash = proof_updates[lvl];
        }
        
        // Update the root if we've made it this far
        if (_key & 2**0 > 0) {
            require(root == keccak256(abi.encodePacked(_proof[0], prior_node_hash)));
            root = keccak256(abi.encodePacked(_proof[0], new_node_hash));
        } else {
            require(root == keccak256(abi.encodePacked(prior_node_hash, _proof[0])));
            root = keccak256(abi.encodePacked(new_node_hash, _proof[0]));
        }
        
        // Tell the others about the update!
        emit UpdatedBranch(_key, _value, proof_updates);
    }

    function set(
        address _acct,
        uint256 _status,
        bytes32[160] _proof
    )
        public
    {
        _set(bytes32(_acct), bytes32(_status), _proof);
    }
}
