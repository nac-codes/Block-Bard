# TESTING.md

This document describes the tests we run to verify blockchain resilience against invalid data.

## 1. Valid chain acceptance

- **Test:** Create a chain of 2–3 blocks with `difficulty=1`.  
- **Expectation:** `Blockchain.is_valid()` returns `True`.

## 2. Tampering with block data

- **Test:** After mining, manually change a block’s `data` field.  
- **Expectation:** `Blockchain.is_valid()` returns `False`.

## 3. Tampering with proof-of-work

- **Test:** After mining, reset a block’s `nonce` (or its `hash`) so it no longer meets the difficulty target.  
- **Expectation:** `Blockchain.is_valid()` returns `False`.

## 4. Rejecting invalid incoming blocks

- **Test A:** Feed a fresh `Blockchain` instance a well-formed block-dict via `add_block_from_dict(...)`.  
  - **Expectation A:** Method returns `True` and chain length increments.

- **Test B:** Feed it a block-dict with the wrong `previous_hash` or an incorrect `hash`.  
  - **Expectation B:** Method returns `False` and chain remains unchanged.

## How to run

```bash
python3 -m unittest discover -v tests
```