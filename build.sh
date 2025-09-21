#!/bin/bash

# Upgrade pip first
pip install --upgrade pip

# Install Python dependencies with verbose output
pip install -r requirements.txt --verbose

# Verify Flask installation
python -c "import flask; print(f'Flask version: {flask.__version__}')"

# Initialize the database
python db.py
