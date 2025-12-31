#!/bin/sh

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Execute the command passed to the docker container
exec "$@"
