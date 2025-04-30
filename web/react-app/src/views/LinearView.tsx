import React, { useState } from 'react';
import { Box, Container, Typography, Pagination, CircularProgress } from '@mui/material';
import BlockCard from '../components/BlockCard';
import { Block } from '../services/api';

interface LinearViewProps {
  blocks: Block[];
  loading: boolean;
}

const LinearView: React.FC<LinearViewProps> = ({ blocks, loading }) => {
  const [page, setPage] = useState(1);
  const blocksPerPage = 5;
  
  // Filter out genesis block
  const contentBlocks = blocks.filter(block => block.index > 0);
  
  // Calculate pagination
  const pageCount = Math.ceil(contentBlocks.length / blocksPerPage);
  const paginatedBlocks = contentBlocks.slice(
    (page - 1) * blocksPerPage,
    page * blocksPerPage
  );
  
  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    // Scroll to top
    window.scrollTo(0, 0);
  };
  
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" my={4}>
        <CircularProgress />
      </Box>
    );
  }
  
  if (contentBlocks.length === 0) {
    return (
      <Box my={4}>
        <Typography variant="body1" align="center">No blocks in the chain yet.</Typography>
      </Box>
    );
  }
  
  return (
    <Container maxWidth="md">
      <Box my={4}>
        <Typography variant="h5" component="h2" gutterBottom>
          Chronological View
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          Showing blocks in the order they were added to the blockchain.
        </Typography>
        
        {paginatedBlocks.map(block => (
          <BlockCard key={block.hash} block={block} />
        ))}
        
        {pageCount > 1 && (
          <Box display="flex" justifyContent="center" mt={4}>
            <Pagination 
              count={pageCount} 
              page={page} 
              onChange={handlePageChange}
              color="primary"
            />
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default LinearView; 