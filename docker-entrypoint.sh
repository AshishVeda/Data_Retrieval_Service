#!/bin/bash
set -e

# Wait for MySQL to be ready
echo "Waiting for MySQL..."
while ! nc -z db 3306; do
  sleep 1
done
echo "MySQL is ready!"

# Run the application
if [ "$FLASK_ENV" = "development" ]; then
  echo "Starting Flask development server..."
  python -m flask run --host=0.0.0.0
else
  echo "Starting production server with gunicorn..."
  gunicorn --bind 0.0.0.0:5000 'app:create_app()'
fi 