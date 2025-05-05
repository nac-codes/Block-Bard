# Block-Bard: Blockchain-based Collaborative Storytelling Platform

![Block-Bard Tree View](web/static/Screenshot%202025-05-04%20at%2022.48.38.png)

## Executive Summary

Block-Bard is a decentralized application for collaborative storytelling using blockchain technology and AI agents. It enables multiple AI agents to contribute to a cohesive story while ensuring structural integrity through a specialized blockchain implementation. The system introduces the novel concept of "story position" to maintain narrative coherence while allowing for branching storylines.

## Core Components

### 1. Blockchain Architecture

The Block-Bard blockchain extends traditional blockchain principles with specialized features for storytelling:

#### Blockchain Design:
- **Basic Structure**: Follows a standard blockchain pattern with blocks linked by cryptographic hashes
- **Proof of Work**: Uses a simple difficulty-based mining system (adjustable difficulty parameter)
- **Consensus**: Longest chain rule with additional position validation
- **Genesis Block**: Special initial block with position hash derived from `{"book": 0, "chapter": 0, "verse": 0}`

#### Key Innovations:
- **Position Hashes**: Each block contains a unique position hash generated from structured position data (e.g., `{"book": 1, "chapter": 1, "verse": 1}`)
- **Position Validation**: The blockchain enforces that no duplicate positions can exist in the chain
- **Story Branching**: Previous position references enable branching narratives while maintaining coherence
- **Structure Enforcement**: Validates that referenced previous positions actually exist in the chain

#### Block Structure:
- Standard blockchain fields: index, timestamp, data, previous hash, nonce, hash
- Extended fields:
  - `author`: Identifies which node/agent created the block
  - `position_hash`: Unique hash derived from the block's story position 
  - `previous_position_hash`: Reference to the position this block continues from

### 2. Peer-to-Peer Network Protocol

The P2P network uses a simple but effective design to maintain blockchain consensus across nodes:

#### Network Architecture:
- **Centralized Tracker**: A lightweight central tracker manages peer discovery
- **Direct Peer Communication**: Nodes exchange blocks and chain data directly
- **Simple Command Protocol**: Text-based commands for peer discovery and block exchange

#### Protocol Commands:
- **Tracker Commands**:
  - `JOIN <peer_addr>`: Register with the tracker
  - `LEAVE <peer_addr>`: Unregister from the tracker
  - `GETPEERS`: Retrieve the list of active peers
- **Node Commands**:
  - `BLOCK <json_data>`: Send a newly mined block to peers
  - `GETCHAIN`: Request the full blockchain from a peer
  - `CHAIN <json_data>`: Response containing the full blockchain

#### Synchronization Process:
1. New nodes register with the tracker and fetch the peer list
2. Nodes sync to the longest valid chain upon startup
3. When mining a new block, nodes broadcast it to all peers
4. Receiving nodes validate the block (including position validation) before adding it
5. Out-of-order blocks trigger a full chain sync to resolve conflicts

#### Conflict Resolution:
- Position conflicts are rejected rather than resolved - a unique design choice for storytelling
- Chain conflicts (forks) are resolved using standard longest chain rule, after validating position uniqueness
- Duplicate position hashes are explicitly rejected, maintaining story coherence

### 3. AI Storytelling Agents

AI agents contribute story content within the blockchain's structural framework:

#### Agent Design:
- **StoryTeller**: Core class that generates structured story content using OpenAI's API
- **MiningAgent**: Manages the interaction between AI generation and blockchain mining
- **Schema-Driven**: Story structure is defined by JSON schemas

#### Storytelling Process:
1. Agent examines the current blockchain to understand story context
2. Agent identifies valid story positions, including existing positions to branch from
3. StoryTeller generates a new story segment with:
   - A unique position in the story structure
   - A reference to an existing position it continues from
   - Content that maintains narrative coherence
4. MiningAgent creates a block with the structured content and attempts to mine it
5. On success, the block is broadcast to other nodes

#### Position Management:
- Agents track previously failed positions to avoid repeating rejected attempts
- Content is structured according to a schema (e.g., Bible-style with books, chapters, verses)
- Each agent includes its node ID, encouraging diverse contributions

#### Schema System:
- JSON schemas define the structure of story content
- Various story formats are supported (Bible, novel, poetry, etc.)
- Schemas include required fields for position data and content
- Custom system prompts can be used to influence AI personality and style

### 4. Web Interface

The web application visualizes the blockchain and story structure:

#### User Interface:
- **React-based** frontend with Material UI components
- **Dual Visualization Modes**:
  - **Linear View**: Chronological presentation of blocks as they were added to the chain
  - **Tree View**: Interactive graph showing the branching structure of the story

#### Tree View Features:
- Interactive node graph with parent-child relationships using ReactFlow
- Nodes contain story content, position data, and author information
- Responsive layout that adjusts to the story structure
- Automatic positioning with user interaction capabilities
- Visualizes the branching narrative structure as a directed graph

#### Linear View Features:
- Chronological presentation of blocks by mining timestamp
- Pagination for easy navigation through long chains
- Detailed block information including content, position, and author

## Novel Story Position Mechanism

The story position feature is a key innovation addressing a fundamental challenge in decentralized storytelling:

### Problem Statement:
In a traditional blockchain, multiple nodes could independently create content for the same logical position in a story, resulting in narrative inconsistencies and duplicate content. For example:
- Node A creates content for "Chapter 1, Verse 2"
- Node B independently creates different content for "Chapter 1, Verse 2"
- Both are valid blocks in blockchain terms, but create story inconsistency

### Solution:
- Each story segment must declare its exact position in the narrative structure
- The blockchain enforces position uniqueness through the position hash mechanism
- Position references create a directed acyclic graph (DAG) of story segments
- Branching is explicitly supported by allowing multiple children of the same parent position

### Implementation Details:
- Position data is structured (e.g., `{"book": 1, "chapter": 2, "verse": 3}`)
- Position hashes are generated using JSON stringification and SHA-256 hashing
- The blockchain validates both:
  - Position uniqueness: No duplicates allowed
  - Position references: Referenced previous positions must exist
- Blocks include both current position and reference to previous position

### Benefits:
- Maintains narrative coherence despite decentralized authorship
- Supports non-linear storytelling through explicit branching
- Provides clear visualization of story structure
- Allows AI agents to understand and contribute to the story's logical structure
- Prevents duplicate story positions while allowing intentional branching

## Implementation Insights

### Technical Choices:
1. **Python Backend**: Lightweight, easy to extend, good AI library support
2. **React Frontend**: Interactive visualization of complex story structures
3. **Simple Text Protocol**: Readable, debuggable network communication
4. **Schema Validation**: Ensures AI-generated content follows required structure
5. **OpenAI Integration**: Leverages advanced language models for storytelling

### Performance Considerations:
- Mining difficulty is kept low for demonstration purposes
- Simple peer discovery through centralized tracker
- In-memory blockchain for simplicity (no persistence)
- Configurable mining intervals with jitter to reduce collision probability

### Design Tradeoffs:
- **Centralized Tracker**: Simplifies peer discovery at the cost of a single point of failure
- **Position Uniqueness**: Prevents duplicate content but increases rejection rate for competing agents
- **JSON Schema Structure**: Provides clear guidance for AI agents but limits flexibility
- **In-memory Storage**: Simplifies implementation but lacks persistence across restarts

### Extensibility:
- **Schema System**: Easily extended with new story formats
- **Agent Personality**: Configurable system prompts for different AI personas
- **Visualization**: UI supports both linear and branching story views
- **Network Protocol**: Simple design allows for easy extension

## File Directory and Descriptions

### Blockchain Module

- **blockchain/blockchain.py**: Implements the core Blockchain class with position validation logic, block addition, consensus mechanisms, and conflict resolution for maintaining chain integrity.
- **blockchain/block.py**: Defines the Block class with specialized attributes for storytelling, including position_hash and previous_position_hash, along with hash calculation and serialization methods.
- **blockchain/__init__.py**: Package initialization file for the blockchain module.

### Network Module

- **network/tracker.py**: Implements the centralized peer tracker that maintains a registry of active nodes and provides peer discovery services through a simple socket-based protocol.
- **network/__init__.py**: Package initialization file for the network module.

### Agent Module

- **agent/storyteller.py**: Core AI integration that uses OpenAI's API to generate structured story content according to schema definitions, with prompt construction to maintain narrative coherence.
- **agent/mining_agent.py**: Manages the storytelling and mining loop, generating content, creating blocks, and broadcasting them to the network with backoff for failures.
- **agent/story_config.py**: Loads and validates story schema configurations from JSON files or predefined schemas.
- **agent/schema_utils.py**: Utilities for working with JSON schemas, including creating Pydantic models for validation of AI-generated content.

### Scripts

- **scripts/run_node.py**: Main entry point for running a Block-Bard node, handling startup, configuration, network registration, blockchain synchronization, and agent initialization.

### Schemas

- **schemas/bible.json**: JSON schema for Bible-style storytelling with books, chapters, and verses.
- **schemas/novel.json**: Schema for novel-style storytelling with parts, chapters, and scenes.
- **schemas/poetry.json**: Schema for poetry with stanzas and lines structure.
- **schemas/template.json**: Base template for creating new schemas.
- **schemas/minimal.json**: Minimal schema for testing and development.
- **schemas/*.txt**: Various system prompts for different AI personalities and storytelling styles.

### Tests

- **tests/**: Contains test scripts for validating blockchain integrity, network communication, and agent behavior.
- **TESTING.md**: Documentation on testing procedures and test case descriptions.

### Web Interface

- **web/react-app/**: React application for visualizing the blockchain and story structure.
  - **src/views/TreeView.tsx**: Implements the branching visualization of story structure as an interactive graph.
  - **src/views/LinearView.tsx**: Implements the chronological view of blocks in the chain.
  - **src/services/api.ts**: Handles data fetching and formatting from the blockchain for the UI.
  - **src/components/**: UI components including BlockCard for displaying story content.

## Conclusion

Block-Bard demonstrates a novel application of blockchain technology to collaborative storytelling. The key innovation of position-based story structure enables coherent, branching narratives despite decentralized authorship. This approach could be extended to other creative collaborative applications where structural integrity is important alongside creative freedom.

The unique combination of blockchain for consensus and structure with AI for content generation creates a powerful platform for decentralized creative collaboration. By introducing the concept of story positions with explicit branching, Block-Bard solves the fundamental challenge of maintaining narrative coherence in a distributed system. 