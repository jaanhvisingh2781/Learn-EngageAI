#!/bin/bash
set -e  # Exit on any error

echo "=== STARTING BUILD PROCESS ==="
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Flask directly first
echo "Installing Flask..."
pip install Flask==2.2.5

# Install gunicorn
echo "Installing gunicorn..."
pip install gunicorn==20.1.0

# Verify installations
echo "Verifying installations..."
python -c "import flask; print(f'Flask {flask.__version__} installed successfully')"

# Initialize database
echo "Initializing database..."
python db.py

echo "=== BUILD COMPLETED SUCCESSFULLY ===" 
