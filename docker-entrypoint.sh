#!/bin/bash
set -e

# No longer waiting for MySQL as we're using AWS RDS directly
echo "Using AWS RDS for database connection..."

# Run the application
if [ "$FLASK_ENV" = "development" ]; then
  echo "Starting Flask development server..."
  python -m flask run --host=0.0.0.0
else
  echo "Starting production server with gunicorn..."
  gunicorn --bind 0.0.0.0:5000 'app:create_app()'
fi 