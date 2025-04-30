import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { 
  Container, 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Snackbar,
  Alert,
  IconButton,
  Box,
  Tooltip
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { ReactFlowProvider } from 'reactflow';

import { fetchBlockchain, Block } from './services/api';
import LinearView from './views/LinearView';
import TreeView from './views/TreeView';

function App() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const loadBlockchain = async () => {
    try {
      setLoading(true);
      setRefreshing(true);
      const data = await fetchBlockchain();
      
      // Check if we actually have new data to update
      const hasChanged = 
        blocks.length !== data.length || 
        (data.length > 0 && blocks.length > 0 && data[data.length-1].hash !== blocks[blocks.length-1].hash);
        
      if (hasChanged) {
        console.log('Blockchain data changed, updating view');
        setBlocks(data);
      } else {
        console.log('No blockchain changes detected');
      }
      
      // Set the last refresh time
      const now = new Date();
      setLastRefresh(now.toLocaleTimeString());
      
      setError(null);
    } catch (err) {
      console.error('Failed to load blockchain:', err);
      setError('Failed to load blockchain data. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Initial load only - no auto-refresh
  useEffect(() => {
    loadBlockchain();
    // No interval for automatic refresh
  }, []);

  const handleRefresh = () => {
    loadBlockchain();
  };

  const handleCloseError = () => {
    setError(null);
  };

  return (
    <ReactFlowProvider>
      <Router>
        <AppBar position="static" color="primary">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Block-Bard Story Viewer
            </Typography>
            <Button color="inherit" component={Link} to="/linear">
              Linear View
            </Button>
            <Button color="inherit" component={Link} to="/tree">
              Mind Map
            </Button>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {lastRefresh && (
                <Tooltip title="Last updated at this time. Manual refresh only.">
                  <Typography variant="caption" sx={{ mr: 1, color: 'rgba(255,255,255,0.7)' }}>
                    Last: {lastRefresh}
                  </Typography>
                </Tooltip>
              )}
              <Tooltip title="Refresh blockchain data">
                <IconButton 
                  color="inherit" 
                  onClick={handleRefresh} 
                  disabled={loading || refreshing}
                >
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/linear" element={<LinearView blocks={blocks} loading={loading} />} />
            <Route path="/tree" element={<TreeView blocks={blocks} loading={loading} />} />
            <Route path="/" element={<Navigate to="/linear" replace />} />
          </Routes>
        </Container>

        <Snackbar open={!!error} autoHideDuration={6000} onClose={handleCloseError}>
          <Alert onClose={handleCloseError} severity="error">
            {error}
          </Alert>
        </Snackbar>
      </Router>
    </ReactFlowProvider>
  );
}

export default App;
