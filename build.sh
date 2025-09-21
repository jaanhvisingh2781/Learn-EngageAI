#!/bin/bash

# Upgrade pip first
pip install --upgrade pip

# Try main requirements, fall back to minimal if it fails
echo "Attempting to install main requirements..."
if pip install -r requirements.txt --no-cache-dir; then
    echo "Main requirements installed successfully"
else
    echo "Main requirements failed, trying minimal requirements..."
    pip install -r requirements_minimal.txt --no-cache-dir
fi

# Verify Flask installation
python -c "import flask; print(f'Flask version: {flask.__version__}')"

# Initialize the database
python db.py
