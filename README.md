# Block-Bard: A Collaborative Blockchain Storytelling Platform

 Block-Bard allows multiple AI nodes to collaboratively create content on a blockchain, with support for branching narratives.

## Prerequisites

- Python 3.8 or higher  
- A virtual environment (venv, conda, etc.)  
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- For AI mode, set your OpenAI API key:
  ```bash
  export OPENAI_API_KEY="sk-<your-secret-key>"
  ```

## Running the Test Suite

```bash
python3 -m unittest discover -v tests
```

## Quick Start

```bash
# Start the tracker
python3 -m scripts.run_tracker

# Start the nodes
python3 scripts/run_node.py --port 50001 --schema novel --system-prompt example_system_prompt.txt

python3 scripts/run_node.py --port 50002 --schema novel --system-prompt example_system_prompt.txt

# View the results in the web UI
./scripts/run_web_dev.sh
```
If have problems running due to module conflicts, try:
```bash
# do 
PYTHONPATH=PATH_TO_PROJECT_ROOT python3 (continue as usual)
```

## Web UI

Before starting, build the react-app
```
cd web/react-app
npm run build
```
Open your browser to:
```
http://localhost:60000
```
Then do:
```bash
# Start the Flask API server
python3 scripts/run_server.py --port 60000

# In another terminal, start the React development server
cd web/react-app && npm start
```
Or use the shortcut:
```bash
./scripts/run_web_dev.sh
```

## Autonomous AI-Agent Mode

1. Start the tracker:
   ```bash
   python3 -m scripts.run_tracker
   ```
2. In separate terminals, start AI nodes:
   ```bash
   python3 scripts/run_node.py --port 50001 --schema bible --system-prompt catholic_prompt.txt
   ```

### Command-Line Options

```
--tracker-host     Tracker host (default: 127.0.0.1)
--tracker-port     Tracker port (default: 8000)
--port             Port for this node to listen on (required)
--schema           Schema to use (bible or path to JSON file)
--mine-interval    Mining interval in seconds (default: 5.0)
--system-prompt    System prompt for AI personality (filepath or direct text)
--api-key          OpenAI API key (defaults to OPENAI_API_KEY environment variable)
--log-level        Set logging level (DEBUG, INFO, WARNING, ERROR)
```

## Example: Biblical Translations with Different Perspectives

Run three nodes with different theological perspectives:

```bash
# Start the tracker
python3 -m scripts.run_tracker

# Start Catholic node
python3 scripts/run_node.py --port 50001 --schema bible --system-prompt catholic_prompt.txt

# Start Protestant node
python3 scripts/run_node.py --port 50002 --schema bible --system-prompt protestant_prompt.txt

# Start Orthodox node
python3 scripts/run_node.py --port 50003 --schema bible --system-prompt orthodox_prompt.txt

# View results in the web UI
./scripts/run_web_dev.sh
```

## Using Custom System Prompts and Schemas

### Custom System Prompt

1. Create a text file with your prompt:
   ```
   You are a [your role] creating a [your content type]. Your task is to:
   1. [instruction 1]
   2. [instruction 2]
   ...
   ```

2. Run a node using your prompt:
   ```bash
   python3 scripts/run_node.py --port 50001 --schema bible --system-prompt /path/to/your_prompt.txt
   ```

### Custom Schema

1. Copy a template schema:
   ```bash
   cp schemas/template.json schemas/my_custom_schema.json
   ```

2. Edit the schema to define your content structure

3. Run a node with your schema:
   ```bash
   python3 scripts/run_node.py --port 50001 --schema /path/to/my_custom_schema.json --system-prompt /path/to/your_prompt.txt
   ```