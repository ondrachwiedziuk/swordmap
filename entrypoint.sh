#!/bin/sh

# Ensure data directory exists
mkdir -p /app/data

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate
python manage.py init_game_data

# Execute the command passed to the docker container
exec "$@"
