# README

## To test

```bash
# Open 2-3 different terminal windows

# First run trackers
python3 -m scripts.run_tracker

# Then run peers
python3 -m scripts.run_peer 127.0.0.1 8000 50000
python3 -m scripts.run_peer 127.0.0.1 8000 50001

# Then server
python3 scripts/run_server.py
# This will provide an address that you can open in the web browser

# To use, simply write the story in terminal and the blockchain should be updated
```