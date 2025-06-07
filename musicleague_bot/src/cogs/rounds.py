import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Modal, TextInput
import datetime
from typing import Optional, List
from ..db import DatabaseService

# Emoji list for voting - supports up to 50 submissions
VOTING_EMOJIS = [
    "🎵", "🎶", "🎤", "🎧", "🎸", "🥁", "🎺", "🎷", "🎹", "🎻",
    "🔥", "⭐", "🌟", "💫", "✨", "🎯", "🏆", "👑", "💎", "🌈",
    "🚀", "⚡", "💥", "🎨", "🌸", "🌺", "🌻", "🌹", "🌼", "🌷",
    "🎀", "🎊", "🎉", "🎈", "🎁", "💝", "💖", "💜", "💙", "💚",
    "❤️", "🧡", "💛", "🤍", "🖤", "💯", "🔮", "🌙", "☀️", "🔶"
]


class SubmissionModal(Modal):
    """Modal for submitting a music entry."""

    def __init__(self, db_service, guild_id):
        super().__init__(title="Submit Music")
        self.db_service = db_service
        self.guild_id = guild_id

        self.submission = TextInput(
            label="Music Link/Title",
            placeholder="Paste a link to your music submission",
            required=True,
            max_length=200,
        )

        self.description = TextInput(
            label="Description (Optional)",
            placeholder="Add context or why you chose this song",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500,
        )

        self.add_item(self.submission)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        # Create submission in database
        submission = await self.db_service.create_submission(
            guild_id=self.guild_id,
            user_id=str(interaction.user.id),
            content=self.submission.value,
            description=self.description.value if self.description.value else None,
        )

        if not submission:
            await interaction.response.send_message(
                "There's no active round to submit to!", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Your submission has been recorded! Thank you for participating.",
            ephemeral=True,
        )



class RoundsCog(commands.Cog):
    """Commands for managing Music League rounds."""

    def __init__(self, bot):
        self.bot = bot
        self.check_rounds.start()

    def cog_unload(self):
        self.check_rounds.cancel()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction additions for voting."""
        # Skip bot reactions
        if user.bot:
            return

        # Check if this is a voting message
        await self._handle_voting_reaction(reaction, user, True)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """Handle reaction removals for voting."""
        # Skip bot reactions
        if user.bot:
            return

        # Check if this is a voting message
        await self._handle_voting_reaction(reaction, user, False)

    async def _handle_voting_reaction(self, reaction, user, is_add):
        """Handle voting reactions (both add and remove)."""
        message = reaction.message
        
        # Check if this message is a voting message for an active round
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)
            
            # Find if this message is a voting message
            from sqlalchemy import text
            query = text("""
                SELECT r.id, r.round_number 
                FROM rounds r 
                JOIN guilds g ON r.guild_id = g.id 
                WHERE r.voting_message_id = :message_id 
                AND r.is_completed = FALSE 
                AND g.guild_id = :guild_id
            """)
            result = await session.execute(query, {
                "message_id": str(message.id),
                "guild_id": str(message.guild.id)
            })
            round_data = result.fetchone()
            
            if not round_data:
                return  # Not a voting message
            
            round_id = round_data[0]
            
            # Check if the reaction emoji is one of our voting emojis
            emoji_str = str(reaction.emoji)
            if emoji_str not in VOTING_EMOJIS:
                return  # Not a voting emoji
            
            # If adding a reaction, enforce the 3-vote limit
            if is_add:
                # Count user's current reactions on this message
                user_reaction_count = 0
                for emoji in VOTING_EMOJIS:
                    try:
                        msg_reaction = discord.utils.get(message.reactions, emoji=emoji)
                        if msg_reaction:
                            users = [u async for u in msg_reaction.users()]
                            if user in users:
                                user_reaction_count += 1
                    except:
                        continue
                
                # If user already has 3 reactions, remove this new one
                if user_reaction_count > 3:
                    try:
                        await message.remove_reaction(reaction.emoji, user)
                    except:
                        pass

    @tasks.loop(
        minutes=5
    )  # Changed from 15 to 5 minutes for faster response to manual transitions
    async def check_rounds(self):
        """Check for rounds that need to transition from submission to voting or to complete."""
        now = datetime.datetime.utcnow()

        # We need to check all guilds
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Get all guilds
            from sqlalchemy import text

            query = text("SELECT id, guild_id FROM guilds")
            guilds = await session.execute(query)

            for guild_row in guilds:
                guild_id = guild_row[1]  # SQLAlchemy returns tuple

                # Get the active round for this guild
                active_round = await db.get_active_round(guild_id)
                if not active_round or active_round.is_completed:
                    continue

                # Check if submission period is over but voting hasn't started
                if (
                    now >= active_round.submission_end
                    and not active_round.voting_message_id
                ):
                    # Transition to voting phase
                    await self.start_voting_phase(db, active_round)

                # Check if voting period is over
                elif now >= active_round.voting_end and not active_round.is_completed:
                    # Complete the round and calculate results
                    await self.complete_round(db, active_round)

    @check_rounds.before_loop
    async def before_check_rounds(self):
        await self.bot.wait_until_ready()

    async def start_voting_phase(self, db, round_obj):
        """Start the voting phase for a round using emoji reactions."""
        # Get guild info without lazy loading
        discord_guild_id, channel_id, voting_days = await db.get_round_guild_info(
            round_obj.id
        )
        if not discord_guild_id:
            return  # Couldn't find guild info

        guild = self.bot.get_guild(int(discord_guild_id))
        if not guild:
            return  # Bot might have left the guild

        # Get submissions
        submissions = await db.get_round_submissions(round_obj.id)

        if not submissions:
            # No submissions, mark as completed
            await db.complete_round(round_obj.id)

            # Use the channel_id we already retrieved
            target_channel = None

            if channel_id:
                target_channel = guild.get_channel(int(channel_id))
                if (
                    target_channel
                    and not target_channel.permissions_for(guild.me).send_messages
                ):
                    target_channel = None

            # If no dedicated channel, find any suitable channel
            if not target_channel:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            # Send the notification
            if target_channel:
                await target_channel.send("The round has ended with no submissions!")

            return

        # Check if we have too many submissions for our emoji set
        if len(submissions) > len(VOTING_EMOJIS):
            # Fallback: truncate to available emojis and send warning
            submissions = submissions[:len(VOTING_EMOJIS)]

        # Create the voting message content
        voting_content = f"# 🎵 Voting for Round #{round_obj.round_number} 🎵\n\n"
        voting_content += f"React with emojis to vote for your favorite submissions! You can vote for up to **3 submissions**.\n"
        voting_content += f"Voting ends <t:{int(round_obj.voting_end.timestamp())}:R>\n\n"

        voting_content += f"**Theme**: {round_obj.theme}\n\n"

        # Add each submission with its emoji
        for idx, submission in enumerate(submissions):
            emoji = VOTING_EMOJIS[idx]
            voting_content += f"{emoji} **Submission #{idx + 1}**\n"
            voting_content += f"{submission.content}\n"
            if submission.description:
                voting_content += f"*{submission.description}*\n"
            voting_content += "\n"

        # Find the target channel
        target_channel = None

        if channel_id:
            # Try to get the dedicated channel
            target_channel = guild.get_channel(int(channel_id))
            if (
                target_channel
                and not target_channel.permissions_for(guild.me).send_messages
            ):
                target_channel = None

        # If no dedicated channel or it wasn't found/accessible, find an appropriate channel
        if not target_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        # If we found a valid channel, send the voting message
        if target_channel:
            try:
                # Split the message if it's too long (Discord's 2000 char limit)
                if len(voting_content) <= 2000:
                    voting_message = await target_channel.send(
                        voting_content, allowed_mentions=discord.AllowedMentions.none()
                    )
                else:
                    # Split into main voting message and details
                    main_content = f"# 🎵 Voting for Round #{round_obj.round_number} 🎵\n\n"
                    main_content += f"React with emojis to vote for your favorite submissions! You can vote for up to **3 submissions**.\n"
                    main_content += f"Voting ends <t:{int(round_obj.voting_end.timestamp())}:R>\n\n"
                    
                    main_content += f"**Theme**: {round_obj.theme}\n\n"
                    
                    main_content += "See submission details below:\n\n"
                    
                    # Add just the emoji and submission number
                    for idx, submission in enumerate(submissions):
                        emoji = VOTING_EMOJIS[idx]
                        main_content += f"{emoji} Submission #{idx + 1}\n"
                    
                    voting_message = await target_channel.send(
                        main_content, allowed_mentions=discord.AllowedMentions.none()
                    )
                    
                    # Send detailed submission info in follow-up messages
                    details_content = ""
                    for idx, submission in enumerate(submissions):
                        emoji = VOTING_EMOJIS[idx]
                        detail_entry = f"{emoji} **Submission #{idx + 1}**\n"
                        detail_entry += f"{submission.content}\n"
                        if submission.description:
                            detail_entry += f"*{submission.description}*\n"
                        detail_entry += "\n"
                        
                        # Check if adding this entry would exceed the limit
                        if len(details_content + detail_entry) > 1900:
                            if details_content:
                                await target_channel.send(
                                    details_content, allowed_mentions=discord.AllowedMentions.none()
                                )
                            details_content = detail_entry
                        else:
                            details_content += detail_entry
                    
                    # Send any remaining details
                    if details_content:
                        await target_channel.send(
                            details_content, allowed_mentions=discord.AllowedMentions.none()
                        )

                # Add emoji reactions for each submission
                for idx, submission in enumerate(submissions):
                    emoji = VOTING_EMOJIS[idx]
                    try:
                        await voting_message.add_reaction(emoji)
                    except discord.HTTPException:
                        # If we can't add a reaction, skip it
                        pass

                # Save the voting message ID
                await db.update_round_message_ids(
                    round_obj.id, voting_message_id=str(voting_message.id)
                )

            except Exception as e:
                # If message creation fails, send an error message
                await target_channel.send(
                    f"Error creating voting message: {str(e)}. Please contact the bot administrator."
                )

    async def _get_username(self, user_id):
        """Helper function to safely get a username from a user ID."""
        try:
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            return user.display_name if user else f"User {user_id}"
        except Exception:
            return f"User {user_id}"
    
    def _get_medal_emoji(self, position):
        """Get a medal emoji based on position."""
        if position == 0:
            return "🥇 "
        elif position == 1:
            return "🥈 "
        elif position == 2:
            return "🥉 "
        return ""
    
    def _format_submission_result(self, idx, submission, submission_index, score, username):
        """Format a result entry for a submission."""
        medal = self._get_medal_emoji(idx)
        voting_emoji = f"{VOTING_EMOJIS[submission_index]} " if submission_index < len(VOTING_EMOJIS) else ""
        
        entry = f"### {medal}{voting_emoji}#{submission_index + 1}: {username} - {score} votes\n"
        entry += f"{submission.content}\n"
        if submission.description:
            entry += f"*{submission.description}*\n"
        entry += "\n"
        
        return entry
    
    async def _format_leaderboard(self, leaderboard):
        """Format the leaderboard section."""
        leaderboard_msg = "## 📊 Current Leaderboard\n\n"
        
        if not leaderboard:
            return leaderboard_msg + "No players yet!\n"
        
        for idx, player in enumerate(leaderboard, 1):
            username = await self._get_username(player.user_id)
            leaderboard_msg += f"#{idx}: {username} - {player.total_score} points\n"
        
        return leaderboard_msg
    
    async def complete_round(self, db, round_obj):
        """Complete a round and calculate results based on emoji reactions."""
        # Get guild info without lazy loading
        discord_guild_id, channel_id, _ = await db.get_round_guild_info(round_obj.id)
        if not discord_guild_id:
            return  # Couldn't find guild info

        guild = self.bot.get_guild(int(discord_guild_id))
        if not guild:
            return  # Bot might have left the guild

        # Get submissions
        submissions = await db.get_round_submissions(round_obj.id)

        # Count emoji reactions if we have a voting message
        if round_obj.voting_message_id:
            # Try to get the voting message from the dedicated channel first
            voting_message = None
            
            if channel_id:
                target_channel = guild.get_channel(int(channel_id))
                if target_channel:
                    try:
                        voting_message = await target_channel.fetch_message(
                            int(round_obj.voting_message_id)
                        )
                    except Exception as e:
                        print(f"Error fetching voting message from dedicated channel: {e}")

            # If we didn't find it in the dedicated channel, search all channels
            if not voting_message:
                for channel in guild.text_channels:
                    try:
                        voting_message = await channel.fetch_message(
                            int(round_obj.voting_message_id)
                        )
                        break
                    except Exception:
                        continue

            # Count reactions for each submission
            if voting_message:
                for idx, submission in enumerate(submissions):
                    if idx < len(VOTING_EMOJIS):
                        emoji = VOTING_EMOJIS[idx]
                        # Find the reaction for this emoji
                        reaction = discord.utils.get(voting_message.reactions, emoji=emoji)
                        if reaction:
                            # Count reactions (subtract 1 for the bot's initial reaction)
                            vote_count = max(0, reaction.count - 1)
                            submission.votes_received = vote_count
                        else:
                            submission.votes_received = 0
                    else:
                        submission.votes_received = 0

                # Commit the vote counts to the database
                await db.session.commit()

        # Calculate results
        results = await db.calculate_round_results(round_obj.id)

        # Create results message
        results_content = f"# 🏆 Results for Round #{round_obj.round_number} 🏆\n\n"
        results_content += "The round has ended! Here are the results:\n\n"
        results_content += f"**Theme**: {round_obj.theme}\n\n"

        # Add each submission to the results with their score
        for idx, (player, submission, submission_index, score) in enumerate(results):
            username = await self._get_username(player.user_id)
            results_content += self._format_submission_result(
                idx, submission, submission_index, score, username
            )

        # Add leaderboard
        leaderboard = await db.get_leaderboard(discord_guild_id, 5)
        results_content += await self._format_leaderboard(leaderboard)

        # Find the target channel for results
        target_channel = None

        if channel_id:
            # Try to get the dedicated channel
            target_channel = guild.get_channel(int(channel_id))
            if (
                target_channel
                and not target_channel.permissions_for(guild.me).send_messages
            ):
                target_channel = None

        # If no dedicated channel or it wasn't found/accessible, find an appropriate channel
        if not target_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        # Only proceed if we have a valid channel
        if target_channel:
            # Split the message if it's too long
            if len(results_content) <= 2000:
                results_message = await target_channel.send(results_content)
            else:
                # Create a main results message with a summary
                main_results = (
                    f"# 🏆 Results for Round #{round_obj.round_number} 🏆\n\n"
                )
                main_results += "The round has ended! Here are the winners:\n\n"

                # Add top 3 only to main message
                for idx, (player, submission, submission_index, score) in enumerate(results[:3]):
                    if idx >= 3:
                        break

                    username = await self._get_username(player.user_id)
                    medal = self._get_medal_emoji(idx)
                    voting_emoji = f"{VOTING_EMOJIS[submission_index]} " if submission_index < len(VOTING_EMOJIS) else ""
                    main_results += f"{medal}{voting_emoji}#{submission_index + 1}: {username} - {score} votes\n"

                results_message = await target_channel.send(main_results)

                # Send detailed results in follow-up messages
                detailed_results = ""
                for idx, (player, submission, submission_index, score) in enumerate(results):
                    username = await self._get_username(player.user_id)
                    entry = self._format_submission_result(
                        idx, submission, submission_index, score, username
                    )

                    # If adding this entry would make the message too long, send what we have and start a new message
                    if len(detailed_results + entry) > 1900:
                        await target_channel.send(detailed_results)
                        detailed_results = entry
                    else:
                        detailed_results += entry

                # Send any remaining detailed results
                if detailed_results:
                    await target_channel.send(detailed_results)

                # Send the leaderboard
                leaderboard_msg = await self._format_leaderboard(leaderboard)
                await target_channel.send(leaderboard_msg)

            # Save the message ID and mark as completed
            await db.complete_round(round_obj.id, str(results_message.id))

    @app_commands.command(name="start", description="Start a new round of Music League")
    @app_commands.describe(theme="Theme for this round (required)")
    async def start_round(self, interaction: discord.Interaction, theme: str):
        """Start a new round of Music League with a specific theme."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Check if there's already an active round
            active_round = await db.get_active_round(str(interaction.guild_id))
            if active_round and not active_round.is_completed:
                await interaction.response.send_message(
                    f"There's already an active round! Round #{active_round.round_number} ends <t:{int(active_round.submission_end.timestamp())}:R>",
                    ephemeral=True,
                )
                return

            # Validate that theme is not empty
            if not theme or theme.strip() == "":
                await interaction.response.send_message(
                    "You must provide a theme for the round. Please try again with a valid theme.",
                    ephemeral=True,
                )
                return

            # Create new round with the required theme
            new_round = await db.create_round(str(interaction.guild_id), theme)

            # Create round announcement
            embed = discord.Embed(
                title=f"🎵 New Music League Round #{new_round.round_number} 🎵",
                description=f"A new round has started! Submit your music with `/submit`.",
                color=discord.Color.blue(),
            )

            # Add theme (now required)
            embed.add_field(name="Theme", value=theme, inline=False)

            embed.add_field(
                name="Submission Deadline",
                value=f"<t:{int(new_round.submission_end.timestamp())}:F> (<t:{int(new_round.submission_end.timestamp())}:R>)",
                inline=False,
            )

            embed.add_field(
                name="Voting Deadline",
                value=f"<t:{int(new_round.voting_end.timestamp())}:F> (<t:{int(new_round.voting_end.timestamp())}:R>)",
                inline=False,
            )

            # Get guild settings
            guild = await db.get_or_create_guild(str(interaction.guild_id))
            dedicated_channel_id = guild.channel_id

            # Respond to the interaction first
            await interaction.response.send_message(
                "Creating new round...", ephemeral=True
            )

            # Check if we should use a dedicated channel
            if dedicated_channel_id:
                channel = interaction.guild.get_channel(int(dedicated_channel_id))
                if (
                    channel
                    and channel.permissions_for(interaction.guild.me).send_messages
                ):
                    message = await channel.send(embed=embed)
                    await db.update_round_message_ids(
                        new_round.id, submission_message_id=str(message.id)
                    )

                    # Update the user's response
                    await interaction.edit_original_response(
                        content=f"Round started! Check <#{channel.id}> for details."
                    )
                    return

            # If no dedicated channel or couldn't send to it, send in the current channel
            message = await interaction.channel.send(embed=embed)
            await db.update_round_message_ids(
                new_round.id, submission_message_id=str(message.id)
            )

            # Update the user's response
            await interaction.edit_original_response(
                content="Round started! See the announcement below."
            )

    @app_commands.command(
        name="submit", description="Submit a song for the current Music League round"
    )
    async def submit(self, interaction: discord.Interaction):
        """Submit a song for the current Music League round."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))

            if not active_round:
                await interaction.response.send_message(
                    "There's no active round! Ask an admin to start a new round with `/start`",
                    ephemeral=True,
                )
                return

            if active_round.is_completed:
                await interaction.response.send_message(
                    "The current round is already completed! Wait for a new round to start.",
                    ephemeral=True,
                )
                return

            # Check if the submission period is over
            now = datetime.datetime.utcnow()
            if now >= active_round.submission_end:
                await interaction.response.send_message(
                    f"The submission period for this round has ended! Voting is now open until <t:{int(active_round.voting_end.timestamp())}:F>",
                    ephemeral=True,
                )
                return

            # Show submission modal
            modal = SubmissionModal(db, str(interaction.guild_id))
            await interaction.response.send_modal(modal)

    @app_commands.command(
        name="status", description="Check the status of the current Music League round"
    )
    async def status(self, interaction: discord.Interaction):
        """Check the status of the current Music League round."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Get the active round
            active_round = await db.get_active_round(str(interaction.guild_id))

            if not active_round:
                embed = discord.Embed(
                    title="Music League Status",
                    description="There's no active round currently. Start a new round with `/start`!",
                    color=discord.Color.blue(),
                )
                await interaction.response.send_message(embed=embed)
                return

            # Create the status embed
            embed = discord.Embed(
                title=f"Music League Round #{active_round.round_number} Status",
                color=discord.Color.blue(),
            )

            embed.add_field(name="Theme", value=active_round.theme, inline=False)

            now = datetime.datetime.utcnow()

            if now < active_round.submission_end:
                # Submission phase
                embed.add_field(
                    name="Status",
                    value=f"Submission Phase - Submit your music with `/submit`",
                    inline=False,
                )

                embed.add_field(
                    name="Submission Deadline",
                    value=f"<t:{int(active_round.submission_end.timestamp())}:F> (<t:{int(active_round.submission_end.timestamp())}:R>)",
                    inline=False,
                )

                # Get current submissions
                submissions = await db.get_round_submissions(active_round.id)
                embed.add_field(
                    name="Submissions",
                    value=f"{len(submissions)} submission(s) so far",
                    inline=False,
                )

            elif now < active_round.voting_end:
                # Voting phase
                embed.add_field(
                    name="Status",
                    value=f"Voting Phase - Cast your votes!",
                    inline=False,
                )

                embed.add_field(
                    name="Voting Deadline",
                    value=f"<t:{int(active_round.voting_end.timestamp())}:F> (<t:{int(active_round.voting_end.timestamp())}:R>)",
                    inline=False,
                )

                # Get submissions
                submissions = await db.get_round_submissions(active_round.id)
                embed.add_field(
                    name="Submissions",
                    value=f"{len(submissions)} submission(s) in this round",
                    inline=False,
                )

            else:
                # Completed or processing
                if active_round.is_completed:
                    embed.add_field(
                        name="Status",
                        value=f"Round completed! Check the results message or start a new round with `/start`",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="Status",
                        value=f"Voting has ended - Results will be calculated soon!",
                        inline=False,
                    )

            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="end_submission",
        description="Forcibly end the submission period and start voting",
    )
    @app_commands.default_permissions(administrator=True)
    async def end_submission(self, interaction: discord.Interaction):
        """Forcibly end the submission period and start the voting phase."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))

            if not active_round:
                await interaction.response.send_message(
                    "There's no active round to modify!", ephemeral=True
                )
                return

            # Check if we're already in voting phase or later
            now = datetime.datetime.utcnow()
            if now >= active_round.submission_end:
                await interaction.response.send_message(
                    "The submission period has already ended!", ephemeral=True
                )
                return

            if active_round.is_completed:
                await interaction.response.send_message(
                    "This round is already completed!", ephemeral=True
                )
                return

            # Get guild info to access the voting days setting
            discord_guild_id, channel_id, voting_days = await db.get_round_guild_info(
                active_round.id
            )
            if not discord_guild_id:
                await interaction.response.send_message(
                    "Error: Could not find guild settings.", ephemeral=True
                )
                return

            # Calculate the new voting end time based on the current time plus voting days
            now = datetime.datetime.utcnow()
            new_voting_end = now + datetime.timedelta(days=voting_days)

            # Update both submission end and voting end times
            await db.update_round_timing(
                active_round.id, submission_end=now, voting_end=new_voting_end
            )

            # We can already find the guild from interaction.guild
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "Error: Could not find the guild this round belongs to.",
                    ephemeral=True,
                )
                return

            # Notify the user that the submission period has ended with updated voting deadline
            await interaction.response.send_message(
                f"Submission period ended! The voting phase will begin shortly (within 5 minutes) and will end <t:{int(new_voting_end.timestamp())}:R>.",
                ephemeral=True,
            )

    @app_commands.command(
        name="end_voting",
        description="Forcibly end the voting period and calculate results",
    )
    @app_commands.default_permissions(administrator=True)
    async def end_voting(self, interaction: discord.Interaction):
        """Forcibly end the voting period and calculate results."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))

            if not active_round:
                await interaction.response.send_message(
                    "There's no active round to modify!", ephemeral=True
                )
                return

            # Check if we're in voting phase
            now = datetime.datetime.utcnow()
            if now < active_round.submission_end:
                await interaction.response.send_message(
                    "The submission period hasn't ended yet! Use `/end_submission` first.",
                    ephemeral=True,
                )
                return

            if now >= active_round.voting_end:
                await interaction.response.send_message(
                    "The voting period has already ended!", ephemeral=True
                )
                return

            if active_round.is_completed:
                await interaction.response.send_message(
                    "This round is already completed!", ephemeral=True
                )
                return

            # Update the voting end time to now
            await db.update_round_timing(active_round.id, voting_end=now)

            # We can already find the guild from interaction.guild
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "Error: Could not find the guild this round belongs to.",
                    ephemeral=True,
                )
                return

            # Notify the user that the voting period has ended
            await interaction.response.send_message(
                "Voting period ended! Results will be calculated shortly with the next check (within 5 minutes).",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(RoundsCog(bot))
