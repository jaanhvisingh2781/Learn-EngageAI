#!/bin/bash

# Simple, reliable build script for Render
echo "Starting build process..."

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --no-cache-dir

# Verify installation
python -c "import flask; print('Flask installed successfully')"

# Initialize the database
echo "Initializing database..."
python db.py

echo "Build completed successfully!"
