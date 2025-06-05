import discord
from discord.ext import commands
import asyncio
import os
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from .db import init_db, get_session

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("musicleague-bot")

# Load environment variables
load_dotenv()


class MusicLeagueBot(commands.Bot):
    """Main bot class for Music League Discord bot."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="!",  # Fallback prefix for text commands
            intents=intents,
            help_command=None,  # We'll use slash commands
        )

        # Store cogs to load
        self.cogs_list = ["cogs.settings", "cogs.rounds"]

    @asynccontextmanager
    async def get_db_session(self):
        """Context manager for database sessions."""
        session = await get_session()
        try:
            yield session
        finally:
            await session.close()

    async def setup_hook(self):
        """Setup hook called when the bot is starting."""
        logger.info("Setting up bot...")

        # Initialize the database
        await init_db()
        logger.info("Database initialized")

        # Load cogs
        for cog in self.cogs_list:
            try:
                await self.load_extension(f"musicleague_bot.src.{cog}")
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}")

    async def on_ready(self):
        """Event fired when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Sync app commands
        await self.tree.sync()
        logger.info("Synced application commands")

    async def on_guild_join(self, guild):
        """Event fired when the bot joins a guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        # Create guild entry in database
        async with self.get_db_session() as session:
            from .db.service import DatabaseService

            db = DatabaseService(session)
            await db.get_or_create_guild(str(guild.id))


def run_bot():
    """Run the Discord bot."""
    bot = MusicLeagueBot()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error(
            "DISCORD_TOKEN not found in environment variables. Please set it in .env file."
        )
        return

    bot.run(token)


if __name__ == "__main__":
    run_bot()
