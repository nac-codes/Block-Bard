import React from 'react';
import { Card, CardContent, CardHeader, Typography, Box, Chip, Paper } from '@mui/material';
import { Block, formatPosition } from '../services/api';

interface BlockCardProps {
  block: Block;
  indentLevel?: number;
}

const BlockCard: React.FC<BlockCardProps> = ({ block, indentLevel = 0 }) => {
  // Skip genesis block
  if (block.index === 0) return null;
  
  const { parsedData } = block;
  
  // Function to render metadata fields in a more readable way
  const renderMetadata = () => {
    if (!parsedData) return null;
    
    // These fields are already handled separately
    const excludedFields = ['Content', 'content', 'storyPosition', 'previousPosition', 'Author', 'author'];
    
    const metadataEntries = Object.entries(parsedData).filter(
      ([key]) => !excludedFields.includes(key)
    );
    
    if (metadataEntries.length === 0) return null;
    
    return (
      <Box mt={2}>
        <Paper variant="outlined" sx={{ p: 1, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {metadataEntries.map(([key, value]) => {
              // Don't display empty values or objects
              if (value === undefined || value === null || value === '') return null;
              
              // Format the value based on its type
              let displayValue = value;
              if (typeof value === 'object') {
                // For objects (like arrays or nested objects), stringify them
                try {
                  displayValue = JSON.stringify(value);
                } catch (e) {
                  displayValue = '[Complex Object]';
                }
              }
              
              // Format key for display (capitalize first letter, add spaces before caps)
              const displayKey = key
                .replace(/([A-Z])/g, ' $1')
                .replace(/^./, (str) => str.toUpperCase());
              
              return (
                <Box key={key} sx={{ flexBasis: '30%', minWidth: '200px' }}>
                  <Typography variant="caption" color="textSecondary">
                    {displayKey}:
                  </Typography>
                  <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                    {typeof displayValue === 'boolean' 
                      ? (displayValue ? 'Yes' : 'No')
                      : displayValue}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Paper>
      </Box>
    );
  };
  
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
              #{block.index} | {parsedData?.Author || block.author || 'Unknown'}
            </Typography>
            {parsedData?.storyPosition && (
              <Chip 
                label={formatPosition(parsedData.storyPosition)}
                size="small"
                color="primary"
              />
            )}
          </Box>
        }
      />
      
      <CardContent>
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
          {parsedData?.Content || parsedData?.content || block.data}
        </Typography>
        
        {renderMetadata()}
        
        {parsedData?.previousPosition && (
          <Box mt={2}>
            <Chip 
              label={`Continues from: ${formatPosition(parsedData.previousPosition)}`}
              size="small"
              color="secondary"
              variant="outlined"
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default BlockCard; 