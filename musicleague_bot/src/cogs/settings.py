import discord
from discord.ext import commands
from discord import app_commands
from ..db import DatabaseService


class SettingsCog(commands.Cog):
    """Commands for configuring the Music League bot."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="settings", description="Configure Music League settings"
    )
    @app_commands.describe(
        submission_days="Number of days for the submission period",
        voting_days="Number of days for the voting period",
        theme_submission_days="Number of days for theme submission period",
        theme_voting_days="Number of days for theme voting period",
        channel="Dedicated channel for Music League messages",
    )
    async def settings(
        self,
        interaction: discord.Interaction,
        submission_days: int = None,
        voting_days: int = None,
        theme_submission_days: int = None,
        theme_voting_days: int = None,
        channel: discord.TextChannel = None,
    ):
        """Configure settings for Music League on this server."""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need 'Manage Server' permission to change settings.",
                ephemeral=True,
            )
            return

        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Update settings
            updated_settings = await db.update_guild_settings(
                guild_id=str(interaction.guild_id),
                submission_days=submission_days,
                voting_days=voting_days,
                theme_submission_days=theme_submission_days,
                theme_voting_days=theme_voting_days,
                channel_id=str(channel.id) if channel else None,
            )

            # Confirm settings back to the user
            embed = discord.Embed(
                title="Music League Settings", color=discord.Color.blue()
            )

            embed.add_field(
                name="Submission Period",
                value=f"{updated_settings.submission_days} days",
            )
            embed.add_field(
                name="Voting Period", value=f"{updated_settings.voting_days} days"
            )
            embed.add_field(
                name="Theme Submission Period", value=f"{updated_settings.theme_submission_days} days"
            )
            embed.add_field(
                name="Theme Voting Period", value=f"{updated_settings.theme_voting_days} days"
            )

            # Add dedicated channel information if set
            if updated_settings.channel_id:
                channel_mention = f"<#{updated_settings.channel_id}>"
                embed.add_field(
                    name="Dedicated Channel", value=channel_mention, inline=False
                )
            else:
                embed.add_field(
                    name="Dedicated Channel",
                    value="None (bot will use any available channel)",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="leaderboard", description="Show the top players in Music League"
    )
    @app_commands.describe(limit="Number of players to show (default: 5)")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 5):
        """Show the leaderboard for Music League on this server."""
        if limit < 1:
            limit = 1
        if limit > 25:
            limit = 25

        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)
            top_players = await db.get_leaderboard(str(interaction.guild_id), limit)

            if not top_players:
                await interaction.response.send_message(
                    "No players in the leaderboard yet!"
                )
                return

            embed = discord.Embed(
                title="🏆 Music League Leaderboard 🏆", color=discord.Color.gold()
            )

            for idx, player in enumerate(top_players, 1):
                user = self.bot.get_user(
                    int(player.user_id)
                ) or await self.bot.fetch_user(int(player.user_id))
                username = user.display_name if user else f"User {player.user_id}"

                # Add medal for top 3
                medal = ""
                if idx == 1:
                    medal = "🥇 "
                elif idx == 2:
                    medal = "🥈 "
                elif idx == 3:
                    medal = "🥉 "

                embed.add_field(
                    name=f"{medal}#{idx} - {username}",
                    value=f"{player.total_score} points",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(SettingsCog(bot))
