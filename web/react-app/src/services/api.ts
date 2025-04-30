import axios from 'axios';

// Types
export interface Position {
  book?: string | number;
  chapter?: number;
  verse?: number;
  title?: string;
  section?: number;
  [key: string]: any;
}

export interface BlockContent {
  Content: string;
  Author?: string;
  storyPosition?: Position;
  previousPosition?: Position;
  [key: string]: any;
}

export interface Block {
  index: number;
  timestamp: number;
  data: string;
  author?: string;
  previous_hash: string;
  hash: string;
  nonce: number;
  position_hash?: string;
  previous_position_hash?: string;
  parsedData?: BlockContent;
}

// API Functions
const API_URL = process.env.REACT_APP_API_URL || '';

export const fetchBlockchain = async (): Promise<Block[]> => {
  try {
    // Set a longer timeout for large chains and disable response size limit
    const options = {
      timeout: 30000, // 30 seconds
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    };

    // For potentially large chains, we'll use pagination
    // First, get just the latest blocks to update the UI quickly
    const latestResponse = await axios.get(`${API_URL}/chain?page=1&per_page=20`, options);
    let allBlocks = latestResponse.data;
    
    // Check if we have more to fetch
    if (allBlocks.length === 20) {
      console.log('Chain might be large, fetching complete chain...');
      
      // Now get the complete chain in the background
      try {
        const fullResponse = await axios.get(`${API_URL}/chain`, options);
        allBlocks = fullResponse.data;
        console.log(`Fetched complete blockchain: ${allBlocks.length} blocks`);
      } catch (err) {
        console.warn('Error fetching complete chain, using partial chain:', err);
      }
    } else {
      console.log(`Fetched complete blockchain: ${allBlocks.length} blocks`);
    }
    
    if (!Array.isArray(allBlocks)) {
      console.error('Invalid blockchain data format, expected array');
      return [];
    }
    
    // Parse block data and enhance with parsedData property
    return allBlocks.map((block: Block) => {
      try {
        // Parse the block data
        const parsedData = JSON.parse(block.data);
        block.parsedData = parsedData;
        
        // Make sure storyPosition is properly formatted
        if (!parsedData.storyPosition && (parsedData.Book || parsedData.Chapter)) {
          parsedData.storyPosition = {
            book: parsedData.Book,
            chapter: parsedData.Chapter,
            verse: parsedData.Verse
          };
        }
        
        // Do the same for previousPosition
        if (!parsedData.previousPosition && parsedData.previousBook) {
          parsedData.previousPosition = {
            book: parsedData.previousBook,
            chapter: parsedData.previousChapter,
            verse: parsedData.previousVerse
          };
        }
        
      } catch (e) {
        console.warn(`Error parsing block #${block.index} data:`, e);
        block.parsedData = { Content: block.data };
      }
      return block;
    });
  } catch (error) {
    console.error('Error fetching blockchain:', error);
    throw error;
  }
};

// Helper functions
export const formatPosition = (position?: Position): string => {
  if (!position) return 'Unknown';
  
  // For bible schema
  if (position.book !== undefined && position.chapter !== undefined && position.verse !== undefined) {
    return `${position.book} ${position.chapter}:${position.verse}`;
  }
  
  // For novel schema
  if (position.title !== undefined && position.chapter !== undefined && position.section !== undefined) {
    return `${position.title} Ch.${position.chapter} §${position.section}`;
  }
  
  // Generic display
  return JSON.stringify(position);
};

export const getPositionKey = (position?: Position): string => {
  if (!position) return 'unknown';
  return JSON.stringify(position);
};

// Build tree structure from blocks
export const buildBlockTree = (blocks: Block[]) => {
  const positionMap = new Map<string, Block>();
  const childrenMap = new Map<string, string[]>();
  const rootNodes: Block[] = [];
  
  console.log('Building tree from blocks:', blocks.length);
  
  // First collect all nodes with positions
  blocks.forEach(block => {
    if (block.index === 0) return; // Skip genesis
    
    if (block.parsedData?.storyPosition) {
      const posKey = getPositionKey(block.parsedData.storyPosition);
      // Check if we already have this position (to avoid duplicates)
      if (!positionMap.has(posKey)) {
        positionMap.set(posKey, block);
      } else {
        console.warn(`Duplicate position found: ${posKey} - Block #${block.index}`);
      }
    } else {
      console.warn(`Block #${block.index} has no storyPosition`);
    }
  });
  
  // Then build parent-child relationships
  blocks.forEach(block => {
    if (block.index === 0) return; // Skip genesis
    
    if (block.parsedData?.storyPosition) {
      const posKey = getPositionKey(block.parsedData.storyPosition);
      
      // Check if this is a root node (no previous position)
      if (!block.parsedData.previousPosition) {
        console.log(`Found root node: Block #${block.index}`);
        rootNodes.push(block);
      } else {
        // Add as a child to its parent
        const parentKey = getPositionKey(block.parsedData.previousPosition);
        
        // Only add if parent exists in our map
        if (positionMap.has(parentKey)) {
          if (!childrenMap.has(parentKey)) {
            childrenMap.set(parentKey, []);
          }
          childrenMap.get(parentKey)?.push(posKey);
        } else {
          console.warn(`Block #${block.index} references non-existent parent position ${parentKey}`);
          // Treat as a root node if parent not found
          rootNodes.push(block);
        }
      }
    }
  });
  
  // Debug tree structure
  console.log('Tree built:',
    {positions: positionMap.size, 
     relationships: childrenMap.size, 
     roots: rootNodes.length,
     rootIndices: rootNodes.map(n => n.index)
    });
  
  return { positionMap, childrenMap, rootNodes };
}; 