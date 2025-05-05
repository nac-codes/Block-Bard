# TESTING.md

This document describes the tests we run to verify blockchain resilience, dynamic difficulty adjustment, fork handling, and P2P networking.

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
- **Description:** Feed it a block-dict with the wrong `previous_hash` or an incorrect `hash`.  
- **Expectation:** Method returns `False` and chain remains unchanged.

## 6. Dynamic difficulty adjustment (`test_dynamic_difficulty_adjusts`)
- **Description:** Mine 5 blocks in succession, allowing the code’s automatic retarget logic to run.  
- **Expectation:** After those blocks, `bc.difficulty` is \>= 1 and different from its initial value.

## 7. Difficulty increases and decreases (`test_difficulty_increases_and_decreases`)
- **Description:**  
  1. Patch `time.time()` to simulate a very fast block (1 s) and call `add_block("fast block")`.  
  2. Expect `bc.difficulty` to have increased by 1.  
  3. Patch `time.time()` to simulate a very slow block (12 s) and call `add_block("slow block")`.  
  4. Expect `bc.difficulty` to have decreased by 1 (down to minimum 1).  
- **Expectation:** Difficulty goes up after a fast block and down after a slow block.

## 8. Fork resolution (competing miners) (`test_competing_miners`)
- **Description:** Simulate two nodes that each mine block #1 on different branches, then one mines block #2.  
- **Expectation:**  
  1. The “losing” node rejects block #2 on its branch.  
  2. Calling `resolve_conflicts(...)` with the longer chain causes it to adopt that chain and return `True`.

## 9. Peer-to-peer network and dynamic peer list (`test_peer_registration_and_discovery`)
- **Description:**  
  1. Start a `Tracker`.  
  2. Have three peers send `JOIN <host:port>`.  
  3. Send `GETPEERS` and verify it returns those three addresses.  
  4. Have one of the peers send `LEAVE <host:port>`.  
  5. Send `GETPEERS` again and verify it returns only the remaining two addresses.  
- **Expectation:**  
  - After the joins, `GETPEERS` returns exactly the three peer addresses.  
  - After the leave, `GETPEERS` returns exactly the two remaining addresses.

## How to run all tests
```bash
python3 -m unittest discover -v tests
```

## Output of the test
```
test_add_block_from_dict_accept (test_blockchain.TestBlockchain.test_add_block_from_dict_accept) ... [Difficulty ↑] Mined in 0.00s → difficulty = 2
[Difficulty ↑] Mined in 0.00s → difficulty = 3
[Blockchain] Adopting remote genesis hash
[Blockchain] Appended block 1
[Blockchain] Appended block 2
ok
test_add_block_from_dict_reject (test_blockchain.TestBlockchain.test_add_block_from_dict_reject) ... [Blockchain] Adopting remote genesis hash
[Blockchain] Hash mismatch
ok
test_difficulty_increases_and_decreases (test_blockchain.TestBlockchain.test_difficulty_increases_and_decreases) ... [Difficulty ↑] Mined in 1.00s → difficulty = 3
[Difficulty ↓] Mined in 12.00s → difficulty = 2
ok
test_dynamic_difficulty_adjusts (test_blockchain.TestBlockchain.test_dynamic_difficulty_adjusts) ... [Difficulty ↑] Mined in 0.00s → difficulty = 2
[Difficulty ↑] Mined in 0.00s → difficulty = 3
[Difficulty ↑] Mined in 0.00s → difficulty = 4
[Difficulty ↑] Mined in 0.00s → difficulty = 5
[Difficulty ↑] Mined in 0.00s → difficulty = 6
ok
test_tamper_data (test_blockchain.TestBlockchain.test_tamper_data) ... [Difficulty ↑] Mined in 0.00s → difficulty = 2
ok
test_tamper_pow (test_blockchain.TestBlockchain.test_tamper_pow) ... [Difficulty ↑] Mined in 0.00s → difficulty = 3
ok
test_valid_chain (test_blockchain.TestBlockchain.test_valid_chain) ... ok
test_competing_miners (test_fork_resolution.TestForkResolution.test_competing_miners) ... [Difficulty ↑] Mined in 0.00s → difficulty = 2
[Difficulty ↑] Mined in 0.00s → difficulty = 2
[Difficulty ↑] Mined in 0.00s → difficulty = 3
[Blockchain] Previous hash does not match latest block
ok
test_peer_registration_and_discovery (test_network.TestP2PNetwork.test_peer_registration_and_discovery) ... Tracker listening on 127.0.0.1:10000
[+] Registered peer: peer0.local:50000
[+] Registered peer: peer1.local:50001
[+] Registered peer: peer2.local:50002
[-] Unregistered peer: peer1.local:50001
ok

----------------------------------------------------------------------
Ran 9 tests in 3.220s

OK
```