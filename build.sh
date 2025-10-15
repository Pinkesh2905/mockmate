#!/usr/bin/env bash

# exit on error
set -o errexit

# Install project dependencies
pip install -r requirements.txt

# Collect static files (CSS, JS, etc.) into a single directory
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate