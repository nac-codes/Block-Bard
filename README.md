# README.md

## Prerequisites

- Python 3.8 or higher  
- A virtual environment (venv, conda, etc.)  
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- (AI mode only) Set your OpenAI secret key:
  ```bash
  export OPENAI_API_KEY="sk-<your-secret-key>"
  ```

## Running the Test Suite

```bash
python3 -m unittest discover -v tests
```

## Web UI

1. Start the Flask server (default port 5000, or specify another):
   ```bash
   python3 scripts/run_server.py --port 60000
   ```
2. Open your browser to:
   ```
   http://<host>:60000/
   ```

## Manual “Story Shell” Mode

1. Start the tracker:
   ```bash
   python3 -m scripts.run_tracker
   ```
2. In separate terminals, start two or more peers:
   ```bash
   python3 -m scripts.run_peer 127.0.0.1 8000 50000
   python3 -m scripts.run_peer 127.0.0.1 8000 50001
   ```
3. In each peer shell:
   - Type a line of text and press Enter to mine a block containing that line.  
   - Type `show` to display the full story chain.  
   - Type `exit` or hit Ctrl-C to quit.

## Testing the AI Agent

```bash
python3 -m scripts.test_agent
```

This script runs a quick sanity check of the `StoryTeller` against the OpenAI API (or uses a placeholder on API errors).

## Autonomous AI-Agent Mode

1. Ensure your `OPENAI_API_KEY` is set and you have available quota.  
2. Start the tracker:
   ```bash
   python3 -m scripts.run_tracker
   ```
3. In separate terminals, start two or more AI nodes:
   ```bash
   python3 scripts/run_node 127.0.0.1 8000 50000
   python3 scripts/run_node 127.0.0.1 8000 50001
   ```
   Each node will fetch the chain, generate a new verse via the AI model every 5 seconds, mine it into a block (`author=<node_id>`), and broadcast it.

## Configuration

- **Mining difficulty** is set in the `Blockchain(difficulty=…)` constructor.  
- **AI mining interval** is the `mine_interval` argument to `MiningAgent`.  
- **Node author names** default to `<hostname>:<port>` but can be customized in `run_node.py`.