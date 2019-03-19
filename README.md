# Implementation of a Sparse Merkle Tree (SMT) synchronizer

IDEA: Validate proof to transition root, then emit the proof and have clients
      parse logs to keep their own personal proof up to date
Args: key, value, proof (existing value)
1. Validate proof is correct for existing value
2. Change the value
3. Recompute the merkle root with the updated value
4. Emit the updated proof as an event (an index of which location it touches)

Clients can loop over each emitted event with indices they are interested in
and update their own proofs

#@dev   This function takes a key-value pair and the existing proof required to
#       show that that the value is correct to others. The proof is validated
#       and updated to reflect what it would be with the value modified, and
#       it is then emitted as a log so that others may iterate over transactions
#       to this contract and keep their own personal proofs up to date for changes
#       to keys that affect their own. This has the side benefits of reducing
#       linkability of keys to specific addresses querying them, as well as
#       reducing data storage in the contract by offloading to event storage.
#@param _key    bytes32     key used to lookup existing value and set new one
#@param _value  bytes32     value to update to
#@param _proof  bytes32[N]  proof for N-depth tree

    # NOTE: Clients can subscribe to these events and filter on keys
    #       that match theirs via `bitxor(update.key, my_key)`.
    #       The first K bits that match theirs should be processed
    #       because they are on the same branch (diverging at K+1).
    #       This reduces the total amount of processing the client
    #       does when iterating through logs from this contract.

    # Emit updated proof so those listening at home can follow along
    # through event filtering and sub-path updates
---

Update contracts and test

---

** DONE! **
When syncing...

        h0
       /  \
      h1   h2
     /  \   \
    m    y   ...

let's say branch `y` updates, and I am tracking branch `m`
`h0`, `h1` will update, `h2` will not
but I only care about `y` updating, because it is involved in the joint
in the branch that we have in common.

Therefore given my path `M` and their path `Y`, I update the `i`-th sibling in my proof,
where `i` is the first non-zero bit in the result of the path diff `M XOR Y`

If `M == Y`, then the value of the leaf will be updated
(triggering an overwrite of my tracked value)
