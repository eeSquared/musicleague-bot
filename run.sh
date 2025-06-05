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

# Create a symbolic link to make data persistent
if [ ! -d "/data/db" ]; then
    mkdir -p /data/db
fi

if [ -f "/app/musicleague.db" ] && [ ! -L "/app/musicleague.db" ]; then
    mv /app/musicleague.db /data/db/musicleague.db
fi

if [ ! -L "/app/musicleague.db" ]; then
    ln -s /data/db/musicleague.db /app/musicleague.db
fi

# Run the bot
python3 /app/main.py
