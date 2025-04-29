# Block-Bard: A Collaborative Blockchain Storytelling Platform

Block-Bard allows multiple AI nodes to collaboratively create stories on a blockchain, with support for branching narratives and different writing styles.

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

## Web UI

1. Start the Flask server:
   ```bash
   python3 scripts/run_server.py --port 60000
   ```
2. Open your browser to:
   ```
   http://<host>:60000/
   ```

## Autonomous AI-Agent Mode

1. Start the tracker:
   ```bash
   python3 -m scripts.run_tracker
   ```
2. In separate terminals, start AI nodes with various configurations:
   ```bash
   python3 scripts/run_node.py --port 50000 --schema bible --writing-style biblical
   python3 scripts/run_node.py --port 50001 --schema novel --writing-style adventure
   ```

### Command-Line Options

```
--tracker-host     Tracker host (default: 127.0.0.1)
--tracker-port     Tracker port (default: 8000)
--port             Port for this node to listen on (required)
--schema           Story schema to use (bible, novel, poetry, or path to JSON file)
--writing-style    Writing style (poetic, technical, biblical, etc.)
--themes           Themes, comma-separated (e.g., "adventure,friendship")
--characters       Characters, comma-separated (e.g., "Alice,Bob")
--mine-interval    Mining interval in seconds (default: 5.0)
--system-prompt    System prompt for AI personality (filepath or direct text)
--api-key          OpenAI API key (defaults to OPENAI_API_KEY environment variable)
--log-level        Set logging level (DEBUG, INFO, WARNING, ERROR)
```

## Example: Multiple Biblical Translations

This example demonstrates how to set up three nodes that represent different biblical traditions, each with a unique theological perspective. They'll collaboratively recreate the Bible, but with their own interpretational differences.

### Step 1: Create System Prompts for Each Tradition

Create three files with prompts for each tradition:

**catholic_prompt.txt**
```
You are a Catholic biblical scholar creating a translation of the Bible. You should:
1. Include all 73 books of the Catholic Bible, including the deuterocanonical works
2. Emphasize Church tradition and magisterial authority in your interpretations
3. Include references to the saints and Church Fathers when appropriate
4. Present a translation that aligns with Catholic doctrine on topics like grace, works, and salvation
5. Use traditional Catholic terminology where appropriate (e.g., "Holy Ghost" rather than just "Spirit")
```

**protestant_prompt.txt**
```
You are a Protestant biblical scholar creating a translation of the Bible. You should:
1. Focus on the 66 books of the Protestant canon
2. Emphasize sola scriptura (scripture alone) and the primacy of biblical text
3. Present interpretations consistent with Protestant views on salvation by faith alone
4. Use accessible, contemporary language where possible
5. Include footnotes explaining difficult passages from a Protestant perspective
```

**orthodox_prompt.txt**
```
You are an Eastern Orthodox biblical scholar creating a translation of the Bible. You should:
1. Include the complete Orthodox canon of Scripture
2. Present interpretations consistent with Orthodox tradition and patristic teachings
3. Emphasize theosis, mystery, and the mystical elements of faith
4. Use language that reflects Orthodox liturgical traditions
5. Include elements that reflect the Orthodox understanding of Church history
```

### Step 2: Run the Nodes

Start the tracker:
```bash
python3 -m scripts.run_tracker
```

Start the Catholic node:
```bash
python3 scripts/run_node.py --port 50001 --schema bible --writing-style biblical \
  --system-prompt catholic_prompt.txt \
  --characters "Jesus,Apostles,Saints,Church Fathers" \
  --themes "salvation,tradition,authority"
```

Start the Protestant node:
```bash
python3 scripts/run_node.py --port 50002 --schema bible --writing-style biblical \
  --system-prompt protestant_prompt.txt \
  --characters "Jesus,Apostles,Reformers" \
  --themes "faith,grace,scripture"
```

Start the Orthodox node:
```bash
python3 scripts/run_node.py --port 50003 --schema bible --writing-style biblical \
  --system-prompt orthodox_prompt.txt \
  --characters "Jesus,Apostles,Church Fathers" \
  --themes "theosis,mystery,liturgy"
```

### Step 3: View the Results

Start the web server:
```bash
python3 scripts/run_server.py --port 60000
```

Open your browser to `http://localhost:60000` to see the collaborative Bible taking shape. You'll notice how nodes may:

1. Create different translations of the same verses
2. Branch when theological differences arise
3. Emphasize different aspects based on their tradition
4. Include or exclude certain books based on their canon

This demonstrates Block-Bard's ability to handle collaborative storytelling with competing perspectives and branching narratives.

## Creating Custom Schemas

You can create custom story structures by:
1. Copying `schemas/template.json` to a new file
2. Modifying the JSON schema to define your story structure
3. Running a node with `--schema /path/to/your/custom_schema.json`