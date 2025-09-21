#!/bin/bash

# Start the simple Flask app
echo "Starting LearnEngage AI..."

# Try gunicorn first, fallback to python
if command -v gunicorn &> /dev/null; then
    echo "Starting with Gunicorn..."
    gunicorn --bind 0.0.0.0:$PORT app_simple:app --timeout 120
else
    echo "Starting with Python..."
    python app_simple.py
fi
