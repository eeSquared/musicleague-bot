# Music League Discord Bot

A Discord bot that allows server members to play a Music League game. This bot allows users to submit music entries, vote on submissions, and keep track of scores across multiple rounds.

## Features

- Configure submission and voting period durations
- Start new rounds with optional themes
- Submit music entries via links or text
- Automatic transition from submission to voting periods
- Uses emoji reactions for voting on submissions (supports unlimited submissions, up to 3 votes per player)
- Leaderboards to track player scores
- Server-specific configuration and data

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Discord Bot Token ([Create a bot here](https://discord.com/developers/applications))
- Administrator permissions on the Discord server where you want to add the bot

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/musicleague-bot.git
   cd musicleague-bot
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Copy the `.env.example` file to `.env`
   - Replace `your_discord_token_here` with your actual Discord bot token

   ```bash
   cp .env.example .env
   nano .env  # Edit with your Discord token
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

### Adding the Bot to Your Server

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Navigate to the "OAuth2" tab
4. Under "Scopes", select "bot" and "applications.commands"
5. Under "Bot Permissions", select:
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
   - Use External Emojis
   - Use Slash Commands
   - Create Polls
   - Read Channels
6. Copy the generated URL and open it in your browser
7. Select your server and authorize the bot

## Usage

### Commands

All commands are available as Discord slash commands:

- `/settings submission_days:[days] voting_days:[days] channel:[text channel]` - Configure the duration of submission and voting periods, and optionally set a dedicated channel for Music League messages (Admin only)
- `/start theme:[required]` - Start a new round with the specified theme (theme is required)
- `/submit` - Submit an entry for the current round
- `/status` - Check the current round status
- `/leaderboard limit:[number]` - Show the top players and their scores
- `/end_submission` - Forcibly end the submission period and begin voting phase (Admin only)
- `/end_voting` - Forcibly end the voting period and calculate results (Admin only)

### How to Play

1. An admin configures the bot settings with `/settings` (optional)
   - Set submission and voting period durations
   - Optionally designate a specific channel for all Music League activity
2. Someone starts a new round with `/start` providing a required theme
3. Players submit their entries with `/submit` during the submission period
4. Once the submission period ends naturally (or an admin uses `/end_submission` to force it), voting will automatically open using emoji reactions in the next check cycle (within 5 minutes)
5. Players vote on their favorite submissions by reacting with emojis (up to 3 votes per player)
6. When the voting period ends naturally (or an admin uses `/end_voting` to force it), results will be calculated in the next check cycle (within 5 minutes)
7. A new round can begin!

### Dedicated Channel

If you want to keep Music League activity in a specific channel (recommended):
1. Create a dedicated text channel for Music League in your server
2. Run `/settings channel:#your-channel-name`
3. All round announcements, polls, and results will be posted in this channel

## Database

The bot uses a SQLite database to store all game data. The database file is created in the project directory as `musicleague.db`.

## License

[MIT License](LICENSE)
