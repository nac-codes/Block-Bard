# TESTING.md

This document describes the tests we run to verify blockchain resilience, fork handling, and P2P networking.

## 1. Valid chain acceptance (`test_valid_chain`)
- **Description:** Create a chain of 2–3 blocks with `difficulty=1`.  
- **Expectation:** `Blockchain.is_valid()` returns `True`.

## 2. Tampering with block data (`test_tamper_data`)
- **Description:** After mining, manually change a block’s `data` field.  
- **Expectation:** `Blockchain.is_valid()` returns `False`.

## 3. Tampering with proof-of-work (`test_tamper_pow`)
- **Description:** After mining, reset a block’s `nonce` (or its `hash`) so it no longer meets the difficulty target.  
- **Expectation:** `Blockchain.is_valid()` returns `False`.

## 4. Accepting a valid incoming block (`test_add_block_from_dict_accept`)
- **Description:** Feed a fresh `Blockchain` instance a well-formed block-dict via `add_block_from_dict(...)`.  
- **Expectation:** Method returns `True` and chain length increments.

## 5. Rejecting an invalid incoming block (`test_add_block_from_dict_reject`) 
- **Description:** Feed it a block-dict with a wrong `previous_hash` or incorrect `hash`.  
- **Expectation:** Method returns `False` and chain remains unchanged.

## 6. Fork resolution (competing miners) (`test_competing_miners`)
- **Description:** Simulate two nodes that each mine block #1 on different branches, then one mines block #2.  
- **Expectation:** The “losing” node rejects block #2 on its branch, then `resolve_conflicts(...)` replaces its chain with the longer one.

## 7. Peer-to-peer network (`test_peer_registration_and_discovery`)
- **Description:** Start a `Tracker`, have three peers send `JOIN host:port`, then send `GETPEERS`.  
- **Expectation:** `GETPEERS` returns exactly those three peer addresses.

## How to run all tests
```bash
python3 -m unittest discover -v tests
```

## Output of the test
```
test_add_block_from_dict_accept (test_blockchain.TestBlockchain.test_add_block_from_dict_accept) ... [Blockchain] Adopting remote genesis hash
[Blockchain] Appended block 1
[Blockchain] Appended block 2
ok
test_add_block_from_dict_reject (test_blockchain.TestBlockchain.test_add_block_from_dict_reject) ... [Blockchain] Adopting remote genesis hash
[Blockchain] Hash mismatch
ok
test_tamper_data (test_blockchain.TestBlockchain.test_tamper_data) ... ok
test_tamper_pow (test_blockchain.TestBlockchain.test_tamper_pow) ... ok
test_valid_chain (test_blockchain.TestBlockchain.test_valid_chain) ... ok
test_competing_miners (test_fork_resolution.TestForkResolution.test_competing_miners) ... [Blockchain] Previous hash does not match latest block
ok
test_peer_registration_and_discovery (test_network.TestP2PNetwork.test_peer_registration_and_discovery) ... Tracker listening on 127.0.0.1:10000
[+] Registered peer: peer0.local:50000
[+] Registered peer: peer1.local:50001
[+] Registered peer: peer2.local:50002
ok

----------------------------------------------------------------------
Ran 7 tests in 0.107s

OK
```