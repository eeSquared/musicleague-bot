#!/usr/bin/env bashio

# Set config path
CONFIG_PATH=/data/options.json

# Validate JSON format
if ! jq . "$CONFIG_PATH" >/dev/null 2>&1; then
    bashio::log.error "Invalid JSON format in options.json"
    exit 1
fi

# Get configuration values directly from JSON
DISCORD_TOKEN=$(jq -r '.discord_token' "$CONFIG_PATH")
PREFIX=$(jq -r '.prefix' "$CONFIG_PATH")
SUBMISSION_DAYS=$(jq -r '.submission_days' "$CONFIG_PATH")
VOTING_DAYS=$(jq -r '.voting_days' "$CONFIG_PATH")

# Check if required configuration is provided
if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "null" ]; then
    bashio::log.error "Discord token is required. Please configure it in the add-on settings."
    exit 1
fi

# Create environment file
echo "DISCORD_TOKEN=$DISCORD_TOKEN" > /app/.env
echo "PREFIX=$PREFIX" >> /app/.env
echo "SUBMISSION_DAYS=$SUBMISSION_DAYS" >> /app/.env
echo "VOTING_DAYS=$VOTING_DAYS" >> /app/.env

# Debug: Print .env file content (excluding token)
bashio::log.info "Created .env file with content:"
grep -v "DISCORD_TOKEN" /app/.env

# Display information
bashio::log.info "Starting Music League Bot..."
bashio::log.info "Submission period: ${SUBMISSION_DAYS} days"
bashio::log.info "Voting period: ${VOTING_DAYS} days"

# Create a directory for persistent storage
bashio::log.info "Setting up persistent database storage..."
if [ ! -d "/data/db" ]; then
    mkdir -p /data/db
    bashio::log.info "Created /data/db directory"
fi

# Check for existing database and move it to persistent storage
if [ -f "/app/musicleague.db" ] && [ ! -L "/app/musicleague.db" ]; then
    bashio::log.info "Moving database to persistent storage"
    mv /app/musicleague.db /data/db/musicleague.db
fi

# Make sure the database file exists in persistent storage
if [ ! -f "/data/db/musicleague.db" ]; then
    bashio::log.info "Creating empty database file"
    touch /data/db/musicleague.db
fi

# Remove any existing symlink before creating a new one
if [ -L "/app/musicleague.db" ]; then
    bashio::log.info "Removing existing symlink"
    rm /app/musicleague.db
fi

# Create a symbolic link to the persistent database
bashio::log.info "Creating symlink to persistent database"
ln -s /data/db/musicleague.db /app/musicleague.db

# Set environment variable to use the symlinked database
echo "DATABASE_URL=sqlite:///musicleague.db" >> /app/.env
bashio::log.info "Database configured at /data/db/musicleague.db"

# Debug: Show file status
bashio::log.info "File checks:"
ls -la /app/musicleague.db
ls -la /data/db/
df -h /data

# Run the bot with detailed logging
bashio::log.info "Starting Music League Bot..."
cd /app
python3 -u /app/main.py
