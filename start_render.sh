#!/bin/bash

# Start the Flask app
echo "Starting LearnEngage AI..."
echo "Port: $PORT"

# Try gunicorn first, fallback to python
if command -v gunicorn &> /dev/null; then
    echo "Starting with Gunicorn..."
    gunicorn --bind 0.0.0.0:$PORT app:app --timeout 120 --workers 1
else
    echo "Starting with Python..."
    python app.py
fi
