#!/usr/bin/env bashio

# Get configuration values
CONFIG_PATH=/data/options.json
DISCORD_TOKEN=$(bashio::config 'discord_token')
PREFIX=$(bashio::config 'prefix')
SUBMISSION_DAYS=$(bashio::config 'submission_days')
VOTING_DAYS=$(bashio::config 'voting_days')

# Check if required configuration is provided
if [ -z "$DISCORD_TOKEN" ]; then
    bashio::log.error "Discord token is required. Please configure it in the add-on settings."
    exit 1
fi

# Create environment file
echo "DISCORD_TOKEN=$DISCORD_TOKEN" > /app/.env
echo "PREFIX=$PREFIX" >> /app/.env
echo "SUBMISSION_DAYS=$SUBMISSION_DAYS" >> /app/.env
echo "VOTING_DAYS=$VOTING_DAYS" >> /app/.env

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
