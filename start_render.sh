#!/bin/bash

# Check if gunicorn is available, otherwise use python directly
if command -v gunicorn &> /dev/null; then
    echo "Starting with Gunicorn..."
    gunicorn --bind 0.0.0.0:$PORT app:app
else
    echo "Gunicorn not found, starting with Python..."
    python app.py
fi
