#!/bin/bash

# Set up PYTHONPATH, not necessary but useful
# export PYTHONPATH=$PYTHONPATH:/Users/chim/Working/computer_networks/block_bard_v3/Block-Bard

# Start the Flask server in the background
echo "Starting Flask API server on port 60000..."
python scripts/run_server.py &
FLASK_PID=$!

# Start the React development server
echo "Starting React development server..."
cd web/react-app && npm start

# When React server is terminated, also kill the Flask server
kill $FLASK_PID