#!/bin/bash

# Start the Flask application with Gunicorn for production
gunicorn --bind 0.0.0.0:$PORT app:app