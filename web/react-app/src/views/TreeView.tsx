import React, { useCallback, useMemo, useEffect, useState } from 'react';
import { Box, Container, Typography, CircularProgress, Button } from '@mui/material';
import ReactFlow, { 
  Node, 
  Edge, 
  Background, 
  Controls,
  Panel,
  useReactFlow,
  MarkerType,
  Viewport,
  OnMove,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Block, buildBlockTree, getPositionKey, formatPosition } from '../services/api';

interface FlowWithProviderProps {
  nodes: Node[];
  edges: Edge[];
  nodeTypes: any;
  onInit: () => void;
  onlyFitViewOnInit?: boolean;
}

// Wrap ReactFlow to ensure proper initialization
const FlowWithProvider: React.FC<FlowWithProviderProps> = ({ nodes, edges, nodeTypes, onInit, onlyFitViewOnInit }) => {
  const reactFlowInstance = useReactFlow();
  const [isInitialRender, setIsInitialRender] = useState(true);
  const [userInteracted, setUserInteracted] = useState(false);
  
  // Store viewport between renders to prevent resetting on data update
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, zoom: 0.5 });
  
  // Track if the user has interacted with the view
  const handleUserInteraction = useCallback(() => {
    if (!userInteracted) {
      setUserInteracted(true);
    }
  }, [userInteracted]);
  
  // Handle initial render with fitView
  useEffect(() => {
    if (isInitialRender && nodes.length > 0) {
      setTimeout(() => {
        if (reactFlowInstance) {
          reactFlowInstance.fitView({ padding: 0.3 });
          setIsInitialRender(false);
        }
      }, 300);
    }
  }, [isInitialRender, nodes, reactFlowInstance]);
  
  // Only adjust viewport on node changes if user hasn't interacted
  useEffect(() => {
    if (nodes.length > 0 && !userInteracted && !isInitialRender) {
      // Skip auto-fit if user has manually positioned the view
      setTimeout(() => {
        if (reactFlowInstance) {
          reactFlowInstance.fitView({ padding: 0.3 });
        }
      }, 300);
    }
  }, [nodes.length, reactFlowInstance, userInteracted, isInitialRender]);
  
  // Save viewport when it changes, but wrapped in useCallback to prevent too many renders
  const handleViewportChange: OnMove = useCallback((_, newViewport) => {
    // Only update if significantly different to avoid render loops
    const viewportChanged = 
      Math.abs(viewport.x - newViewport.x) > 5 || 
      Math.abs(viewport.y - newViewport.y) > 5 || 
      Math.abs(viewport.zoom - newViewport.zoom) > 0.05;
      
    if (viewportChanged) {
      setViewport(newViewport);
    }
  }, [viewport]);
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onInit={onInit}
      fitView={isInitialRender}
      fitViewOptions={{ padding: 0.3 }}
      minZoom={0.1}
      maxZoom={1.5}
      defaultViewport={viewport}
      onMove={handleViewportChange}
      onMoveStart={handleUserInteraction}
      onNodeDragStart={handleUserInteraction}
      onClick={handleUserInteraction}
      nodesDraggable={true}
      elementsSelectable={true}
    >
      <Background color="#f8f8f8" gap={16} />
      <Controls />
      <Panel position="top-right">
        <Button 
          variant="contained" 
          size="small"
          onClick={() => {
            reactFlowInstance.fitView({ padding: 0.3 });
            setUserInteracted(false);
          }}
        >
          Center View
        </Button>
      </Panel>
    </ReactFlow>
  );
};

// Custom node types
const CustomNode = ({ data }: { data: any }) => {
  if (!data || !data.block) {
    return (
      <div style={{ padding: '10px', background: '#ffeeee', border: '1px solid red' }}>
        Invalid Node Data
      </div>
    );
  }
  
  const { block } = data;
  const { parsedData } = block;
  
  return (
    <div style={{ 
      padding: '15px',
      borderRadius: '8px',
      background: '#fff',
      border: '1px solid #ddd',
      width: '280px',
      fontSize: '12px',
      boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
    }}>
      {/* Add handles for edge connections - these are invisible connection points */}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        style={{ background: '#555', visibility: 'hidden' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        style={{ background: '#555', visibility: 'hidden' }}
      />
      
      <div style={{ 
        borderBottom: '1px solid #eee', 
        marginBottom: '8px', 
        display: 'flex',
        justifyContent: 'space-between',
        paddingBottom: '8px'
      }}>
        <strong>#{block.index}</strong>
        <span style={{ fontWeight: 'bold', color: '#0066cc' }}>
          {formatPosition(parsedData?.storyPosition)}
        </span>
      </div>
      <div style={{ 
        fontSize: '13px', 
        maxHeight: '100px', 
        overflow: 'auto', 
        marginBottom: '8px',
        padding: '5px',
        background: '#f9f9f9',
        borderRadius: '4px'
      }}>
        {parsedData?.Content || ''}
      </div>
      <div style={{ 
        fontSize: '11px',
        display: 'flex',
        justifyContent: 'space-between',
        color: '#666'
      }}>
        <span>Author: {block.author || 'Unknown'}</span>
        {parsedData?.previousPosition && (
          <span>From: {formatPosition(parsedData?.previousPosition)}</span>
        )}
      </div>
    </div>
  );
};

interface TreeViewProps {
  blocks: Block[];
  loading: boolean;
}

const TreeView: React.FC<TreeViewProps> = ({ blocks, loading }) => {
  const reactFlowInstance = useReactFlow();
  
  // Fix: Memoize nodeTypes to prevent recreation on each render
  const nodeTypes = useMemo(() => ({
    customNode: CustomNode,
  }), []);
  
  // State to track if debugging info should be shown
  const [showDebug, setShowDebug] = useState(false);
  
  // Track previous block count to avoid unnecessary rebuilds
  const [prevBlockCount, setPrevBlockCount] = useState(0);
  
  // Setup initial state for tree data
  const [treeData, setTreeData] = useState<{
    positionMap: Map<string, Block>;
    childrenMap: Map<string, string[]>;
    rootNodes: Block[];
  }>({
    positionMap: new Map(),
    childrenMap: new Map(),
    rootNodes: []
  });
  
  // Check if we need to rebuild the tree when blocks change
  useEffect(() => {
    // Compare if we have new blocks
    const currentBlockCount = blocks.length;
    const hasNewBlocks = currentBlockCount > prevBlockCount;
    
    if (hasNewBlocks || (currentBlockCount > 0 && treeData.positionMap.size === 0)) {
      console.log('Building new tree due to changes:', currentBlockCount);
      
      // Build new tree
      const result = buildBlockTree(blocks);
      setTreeData(result);
      setPrevBlockCount(currentBlockCount);
      
      // Debug info
      console.log('Tree structure updated:', {
        blocks: blocks.length,
        positionMap: result.positionMap.size,
        childrenMap: result.childrenMap.size,
        rootNodes: result.rootNodes.length
      });
    }
  }, [blocks, prevBlockCount, treeData.positionMap.size]);
  
  // Use the tree data to create nodes and edges
  const { positionMap, childrenMap, rootNodes } = treeData;
  
  // Create nodes and edges for ReactFlow with improved layout
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    
    // Improved horizontal spacing between siblings
    const HORIZONTAL_SPACING = 350;
    // Vertical distance between levels
    const VERTICAL_SPACING = 200;
    
    // Helper function to calculate the total width needed for a subtree
    const calculateSubtreeWidth = (posKey: string): number => {
      const children = childrenMap.get(posKey) || [];
      if (children.length === 0) return HORIZONTAL_SPACING;
      
      let totalWidth = 0;
      children.forEach((childKey: string) => {
        totalWidth += calculateSubtreeWidth(childKey);
      });
      
      return Math.max(totalWidth, HORIZONTAL_SPACING);
    };
    
    // Helper function to recursively build the tree with better positioning
    const buildTree = (block: Block, x: number, y: number, level = 0): number => {
      if (!block.parsedData?.storyPosition) {
        console.log('Block missing storyPosition:', block.index, block.parsedData);
        return 0;
      }
      
      const posKey = getPositionKey(block.parsedData.storyPosition);
      
      // Create node
      nodes.push({
        id: posKey,
        type: 'customNode',
        data: { block },
        position: { x, y },
      });
      
      // Create edges to children
      const children = childrenMap.get(posKey) || [];
      
      if (children.length === 0) return HORIZONTAL_SPACING;
      
      // Calculate total width needed for all children
      let totalWidth = 0;
      children.forEach((childKey: string) => {
        totalWidth += calculateSubtreeWidth(childKey);
      });
      
      // Position each child and connect with edge
      let currentX = x - totalWidth / 2;
      
      children.forEach((childKey: string) => {
        const childBlock = positionMap.get(childKey);
        if (!childBlock) {
          console.log('Missing child block for key:', childKey);
          return;
        }
        
        // Calculate child subtree width
        const childWidth = calculateSubtreeWidth(childKey);
        
        // Center the child within its allocated space
        const childX = currentX + childWidth / 2;
        const childY = y + VERTICAL_SPACING;
        
        // Create edge with arrow and explicit handle IDs
        edges.push({
          id: `edge-${posKey}-${childKey}`,
          source: posKey,
          target: childKey,
          sourceHandle: 'source',  // Match the handle ID from CustomNode
          targetHandle: 'target',  // Match the handle ID from CustomNode
          style: { 
            stroke: '#2B6CB0', 
            strokeWidth: 2
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 15,
            height: 15,
            color: '#2B6CB0',
          },
          // Use curved edges for clearer visualization
          type: 'smoothstep',
          animated: false,
        });
        
        // Recursively build the tree for this child
        const widthUsed = buildTree(childBlock, childX, childY, level + 1);
        currentX += widthUsed;
      });
      
      return totalWidth;
    };
    
    // Position root nodes with adequate spacing
    if (rootNodes.length === 0) {
      console.log('No root nodes found.');
      // If no root nodes, use the first non-genesis block as a fallback
      const nonGenesisBlocks = blocks.filter(b => b.index > 0);
      if (nonGenesisBlocks.length > 0) {
        console.log('Using first block as fallback:', nonGenesisBlocks[0].index);
        buildTree(nonGenesisBlocks[0], 500, 100);
      }
    } else {
      let startX = 0;
      rootNodes.forEach((rootNode: Block) => {
        console.log('Building tree from root node:', rootNode.index);
        const rootWidth = calculateSubtreeWidth(getPositionKey(rootNode.parsedData?.storyPosition || {}));
        startX += rootWidth / 2;
        buildTree(rootNode, startX, 100);
        startX += rootWidth / 2 + 100; // Add extra space between root trees
      });
    }
    
    console.log('Generated flow elements:', { nodes: nodes.length, edges: edges.length });
    return { nodes, edges };
  }, [rootNodes, childrenMap, positionMap, blocks]);
  
  // Handle initial setup
  const onInit = useCallback(() => {
    console.log('ReactFlow initialized');
  }, []);
  
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" my={4}>
        <CircularProgress />
      </Box>
    );
  }
  
  if (blocks.length <= 1) {
    return (
      <Box my={4}>
        <Typography variant="body1" align="center">No blocks in the chain yet.</Typography>
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ height: '80vh' }}>
      <Box my={2} display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h5" component="h2" gutterBottom>
            Mind Map View
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Exploring the branching story structure. Drag to pan, scroll to zoom.
          </Typography>
          {nodes.length === 0 && (
            <Typography variant="body2" color="error.main" sx={{ mt: 1 }}>
              No nodes to display. There might be an issue with the story structure.
            </Typography>
          )}
        </Box>
        <Box>
          <Button 
            variant="outlined" 
            color="primary" 
            size="small"
            onClick={() => setShowDebug(!showDebug)}
          >
            {showDebug ? 'Hide Debug' : 'Show Debug'}
          </Button>
        </Box>
      </Box>
      
      {showDebug && (
        <Box mb={2} p={2} bgcolor="#f5f5f5" borderRadius={1}>
          <Typography variant="subtitle2">Debug Information:</Typography>
          <Typography variant="body2">Total blocks: {blocks.length}</Typography>
          <Typography variant="body2">Root nodes: {rootNodes.length}</Typography>
          <Typography variant="body2">Position mappings: {positionMap.size}</Typography>
          <Typography variant="body2">Parent-child relationships: {childrenMap.size}</Typography>
          <Typography variant="body2">Generated nodes: {nodes.length}</Typography>
          <Typography variant="body2">Generated edges: {edges.length}</Typography>
          {rootNodes.length > 0 && (
            <Typography variant="body2">
              Root node indices: {rootNodes.map((n: Block) => n.index).join(', ')}
            </Typography>
          )}
        </Box>
      )}
      
      <Box sx={{ height: 'calc(80vh - 100px)', border: '1px solid #ddd', borderRadius: '8px' }}>
        {nodes.length > 0 ? (
          <FlowWithProvider 
            nodes={nodes} 
            edges={edges} 
            nodeTypes={nodeTypes} 
            onInit={onInit} 
            onlyFitViewOnInit={true}
          />
        ) : (
          <Box 
            display="flex" 
            alignItems="center" 
            justifyContent="center"
            height="100%"
            flexDirection="column"
            p={3}
            textAlign="center"
          >
            <Typography variant="h6" color="error" gutterBottom>
              Unable to generate mind map
            </Typography>
            <Typography variant="body2">
              The story structure doesn't have proper position relationships.
              Try the Linear View instead to see the story content.
            </Typography>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default TreeView; 