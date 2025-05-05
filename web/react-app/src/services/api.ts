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
// const API_URL = process.env.REACT_APP_API_URL || '';
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:60000';

export const fetchBlockchain = async (): Promise<Block[]> => {
  try {
    // Set a longer timeout for large chains and disable response size limit
    const options = {
      timeout: 60000, // 60 seconds (doubled from 30)
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    };

    console.log('Fetching blockchain data...');
    
    // First, get just the latest blocks with pagination to display quickly
    const latestResponse = await axios.get(`${API_URL}/chain?page=1&per_page=20`, options);
    
    // Debug headers
    console.log('Response headers:', latestResponse.headers);
    
    // Check if we have pagination headers (case-insensitive check)
    const headerKeys = Object.keys(latestResponse.headers).map(k => k.toLowerCase());
    console.log('Available headers:', headerKeys);
    
    // Get header values regardless of case
    const getHeaderCaseInsensitive = (headers: any, key: string): string => {
      const lowerKey = key.toLowerCase();
      const matchingKey = Object.keys(headers).find(k => k.toLowerCase() === lowerKey);
      return matchingKey ? headers[matchingKey] : '';
    };
    
    const totalBlocks = parseInt(getHeaderCaseInsensitive(latestResponse.headers, 'x-total-blocks') || '0');
    const totalPages = parseInt(getHeaderCaseInsensitive(latestResponse.headers, 'x-total-pages') || '0');
    
    console.log(`Pagination info: total blocks=${totalBlocks}, total pages=${totalPages}`);
    
    // Use the partial data initially
    let allBlocks = latestResponse.data;
    
    // If we have more blocks to fetch and pagination info is available
    if (totalBlocks > 20 && totalPages > 1) {
      console.log(`Chain has ${totalBlocks} blocks across ${totalPages} pages, fetching remaining data...`);
      
      try {
        // Fetch remaining pages in parallel
        const pagePromises = [];
        
        // Limit to a reasonable number of parallel requests
        const MAX_PARALLEL_REQUESTS = 3;
        const BLOCKS_PER_PAGE = 20;
        
        // Fetch a few pages at a time to avoid overwhelming the server
        for (let page = 2; page <= totalPages; page += MAX_PARALLEL_REQUESTS) {
          const pageGroup = [];
          
          // Create a batch of promises for pages
          for (let i = 0; i < MAX_PARALLEL_REQUESTS && (page + i) <= totalPages; i++) {
            const currentPage = page + i;
            console.log(`Fetching page ${currentPage}...`);
            pageGroup.push(
              axios.get(`${API_URL}/chain?page=${currentPage}&per_page=${BLOCKS_PER_PAGE}`, options)
                .then(response => {
                  console.log(`Received page ${currentPage} with ${response.data.length} blocks`);
                  return response.data;
                })
                .catch(err => {
                  console.warn(`Error fetching page ${currentPage}:`, err);
                  return []; // Return empty array for failed pages
                })
            );
          }
          
          // Wait for this batch to complete before starting the next
          const pageResults = await Promise.all(pageGroup);
          pagePromises.push(...pageResults);
          
          // Give the server a small break between batches
          if (page + MAX_PARALLEL_REQUESTS <= totalPages) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
        }
        
        // Combine all pages
        let remainingBlocks = pagePromises.flat();
        console.log(`Fetched ${remainingBlocks.length} additional blocks`);
        
        // Combine with first page, ensuring no duplicates
        const seenIndices = new Set(allBlocks.map((block: Block) => block.index));
        
        for (const block of remainingBlocks) {
          if (!seenIndices.has(block.index)) {
            allBlocks.push(block);
            seenIndices.add(block.index);
          }
        }
        
        // Sort by index to ensure proper order
        allBlocks.sort((a: Block, b: Block) => a.index - b.index);
        
        console.log(`Final blockchain has ${allBlocks.length} blocks`);
      } catch (err) {
        console.warn('Error fetching additional pages, using partial data:', err);
      }
    } else if (totalBlocks > 0 && totalBlocks !== allBlocks.length) {
      // If headers indicate more blocks but we couldn't fetch pages, try once more with a direct request
      console.log(`Headers indicate ${totalBlocks} blocks but we received ${allBlocks.length}. Attempting direct fetch...`);
      try {
        const fullResponse = await axios.get(`${API_URL}/chain`, options);
        if (fullResponse.data && Array.isArray(fullResponse.data) && fullResponse.data.length > allBlocks.length) {
          allBlocks = fullResponse.data;
          console.log(`Direct fetch successful, got ${allBlocks.length} blocks`);
        }
      } catch (err) {
        console.warn('Direct fetch failed:', err);
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
  
  // Generic position formatter that works for any schema
  const entries = Object.entries(position);
  
  // Skip internal properties or empty values
  const validEntries = entries.filter(([key, value]) => {
    return key !== 'id' && 
           value !== undefined && 
           value !== null && 
           value !== '' &&
           !key.startsWith('_');
  });
  
  if (validEntries.length === 0) return 'Unknown';
  
  // Format each entry based on its type and create a human-readable representation
  const formattedParts = validEntries.map(([key, value]) => {
    // For numeric values, just show the value
    if (typeof value === 'number') {
      return `${value}`;
    }
    
    // For simple string values, just show the value
    if (typeof value === 'string' && !value.startsWith('{')) {
      return `${value}`;
    }
    
    // For boolean values
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    
    // For objects, try to format them nicely
    if (typeof value === 'object' && value !== null) {
      return `${key}: ${JSON.stringify(value)}`;
    }
    
    // Default case
    return `${key}: ${value}`;
  });
  
  return formattedParts.join(' · ');
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