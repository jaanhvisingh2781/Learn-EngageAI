#!/bin/bash
set -e  # Exit on any error

echo "=== STARTING LEARNENGAGE AI ==="
echo "Port: $PORT"
echo "Python version: $(python --version)"

# Verify Flask is installed
echo "Verifying Flask installation..."
python -c "import flask; print(f'Flask {flask.__version__} is available')"

# Start the application
echo "Starting application..."
python app.py
