#!/usr/bin/env bash
# exit on error
set -o errexit

# --- Poetry Installation (Optional but Recommended) ---
# Uncomment the lines below if you switch to using Poetry for dependency management
# pip install poetry
# poetry config virtualenvs.create false
# poetry install --no-dev --no-interaction --no-ansi

# --- Standard pip Installation ---
echo "---> Installing Python dependencies..."
pip install -r requirements.txt

# --- Frontend Build ---
echo "---> Installing Node.js dependencies..."
npm install

echo "---> Building frontend assets..."
npm run build

# --- NLTK Data Download ---
echo "---> Downloading NLTK data..."
python -m nltk.downloader -d /opt/render/project/src/nltk_data -f nltk.txt

# --- Django Management Commands ---
echo "---> Collecting static files..."
python manage.py collectstatic --no-input

echo "---> Applying database migrations..."
python manage.py migrate
```
