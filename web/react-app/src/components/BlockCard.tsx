import React from 'react';
import { Card, CardContent, CardHeader, Typography, Box, Chip } from '@mui/material';
import { Block, formatPosition } from '../services/api';

interface BlockCardProps {
  block: Block;
  indentLevel?: number;
}

const BlockCard: React.FC<BlockCardProps> = ({ block, indentLevel = 0 }) => {
  // Skip genesis block
  if (block.index === 0) return null;
  
  const { parsedData } = block;
  
  return (
    <Card 
      sx={{ 
        marginBottom: 2, 
        marginLeft: `${indentLevel * 20}px`, 
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}
    >
      <CardHeader
        title={
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1">
              #{block.index} | {block.author || 'Unknown'}
            </Typography>
            <Typography variant="subtitle1" fontWeight="bold">
              {parsedData?.storyPosition 
                ? formatPosition(parsedData.storyPosition) 
                : 'Unknown Position'}
            </Typography>
          </Box>
        }
      />
      
      <CardContent>
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {parsedData?.Content || parsedData?.content || block.data}
        </Typography>
        
        {parsedData?.previousPosition && (
          <Box mt={2}>
            <Chip 
              label={`Continues from: ${formatPosition(parsedData.previousPosition)}`}
              size="small"
              color="primary"
              variant="outlined"
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default BlockCard; 