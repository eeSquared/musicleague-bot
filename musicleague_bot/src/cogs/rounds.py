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


class ThemeSubmissionModal(Modal):
    """Modal for submitting a theme for the next round."""

    def __init__(self, db_service, guild_id):
        super().__init__(title="Submit Theme for Next Round")
        self.db_service = db_service
        self.guild_id = guild_id

        self.theme = TextInput(
            label="Theme Suggestion",
            placeholder="Suggest a theme for the next round",
            required=True,
            max_length=100,
        )

        self.description = TextInput(
            label="Description (Optional)",
            placeholder="Explain your theme idea or give examples",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=300,
        )

        self.add_item(self.theme)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        # Create theme submission in database
        theme_submission = await self.db_service.create_theme_submission(
            guild_id=self.guild_id,
            user_id=str(interaction.user.id),
            theme_text=self.theme.value,
            description=self.description.value if self.description.value else None,
        )

        if not theme_submission:
            await interaction.response.send_message(
                "There's no active round for theme submissions!", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Your theme suggestion has been recorded! Thank you for participating.",
            ephemeral=True,
        )


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
            
            # Find if this message is a regular voting message
            from sqlalchemy import text
            query = text("""
                SELECT r.id, r.round_number, 'music' as voting_type
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
            
            # If not a music voting message, check if it's a theme voting message
            if not round_data:
                theme_query = text("""
                    SELECT r.id, r.round_number, 'theme' as voting_type
                    FROM rounds r 
                    JOIN guilds g ON r.guild_id = g.id 
                    WHERE r.theme_voting_message_id = :message_id 
                    AND r.is_completed = TRUE 
                    AND g.guild_id = :guild_id
                """)
                result = await session.execute(theme_query, {
                    "message_id": str(message.id),
                    "guild_id": str(message.guild.id)
                })
                round_data = result.fetchone()
            
            if not round_data:
                return  # Not a voting message
            
            round_id = round_data[0]
            voting_type = round_data[2]
            
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

            # Also check for completed rounds that need theme phase transitions
            completed_rounds_query = text("""
                SELECT r.id, r.guild_id, r.theme_submission_end, r.theme_voting_end,
                       r.theme_submission_message_id, r.theme_voting_message_id
                FROM rounds r 
                JOIN guilds g ON r.guild_id = g.id 
                WHERE r.is_completed = TRUE 
                AND r.theme_submission_end IS NOT NULL
                AND g.guild_id = r.guild_id
            """)
            completed_rounds = await session.execute(completed_rounds_query)

            for round_row in completed_rounds:
                round_id = round_row[0]
                guild_db_id = round_row[1]
                theme_submission_end = round_row[2]
                theme_voting_end = round_row[3]
                theme_submission_message_id = round_row[4]
                theme_voting_message_id = round_row[5]

                # Get the round object
                completed_round = await db.get_round(round_id)
                if not completed_round:
                    continue

                # Check if theme submission period is over but theme voting hasn't started
                if (
                    theme_submission_end and now >= theme_submission_end
                    and not theme_voting_message_id
                ):
                    # Transition to theme voting phase
                    await self.start_theme_voting_phase(db, completed_round)

                # Check if theme voting period is over
                elif (
                    theme_voting_end and now >= theme_voting_end
                    and theme_voting_message_id
                ):
                    # Complete theme voting (announce results)
                    await self.complete_theme_voting(db, completed_round)

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
                # Send a header message followed by detailed submission info
                main_content = self._format_voting_header(round_obj)
                
                # Send the main voting message
                voting_message = await target_channel.send(
                    main_content, allowed_mentions=discord.AllowedMentions.none()
                )
                
                # Send detailed submission info in follow-up messages
                for idx, submission in enumerate(submissions):
                    detail_entry = self._format_voting_submission_detail(idx, submission)
                    await target_channel.send(
                        detail_entry, allowed_mentions=discord.AllowedMentions.none()
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
    
    def _format_voting_header(self, round_obj):
        """Format the header section of a voting message."""
        header = f"# 🎵 Voting for Round #{round_obj.round_number} 🎵\n\n"
        header += f"React with emojis to vote for your favorite submissions! You can vote for up to **3 submissions**.\n"
        header += f"Voting ends <t:{int(round_obj.voting_end.timestamp())}:R>\n\n"
        header += f"**Theme**: {round_obj.theme}\n\n"
        return header
        
    def _format_voting_submission_detail(self, submission_index, submission):
        """Format detailed submission information for voting messages."""
        emoji = VOTING_EMOJIS[submission_index] if submission_index < len(VOTING_EMOJIS) else "📌"
        detail = f"{emoji} **Submission #{submission_index + 1}**\n"
        detail += f"{submission.content}\n"
        if submission.description:
            detail += f"*{submission.description}*\n"
        detail += "\n"
        return detail

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
            # Always use the same pattern regardless of message length:
            # 1. Send a summary with title
            # 2. Add all detailed results
            # 3. Send the leaderboard
            
            # Create a main results message with a summary
            round_results = (
                f"# 🏆 Results for Round #{round_obj.round_number} 🏆\n\n"
            )
            round_results += f"**Theme**: {round_obj.theme}\n\n"
            round_results += "The round has ended! Here are the winners:\n\n"

            results_message = await target_channel.send(round_results)
            round_results = ""
            # Send detailed results in follow-up messages
            for idx, (player, submission, submission_index, score) in enumerate(results):
                username = await self._get_username(player.user_id)
                entry = self._format_submission_result(
                    idx, submission, submission_index, score, username
                )

                # If adding this entry would make the message too long, send what we have and start a new message
                if len(round_results + entry) > 1900:
                    if round_results:  # Only send if not empty
                        await target_channel.send(round_results)
                    round_results = entry
                else:
                    round_results += entry

            # Send any remaining detailed results
            if round_results:
                await target_channel.send(round_results)

            # Send the leaderboard
            leaderboard_msg = await self._format_leaderboard(leaderboard)
            await target_channel.send(leaderboard_msg)

            # Save the message ID and mark as completed
            await db.complete_round(round_obj.id, str(results_message.id))

            # Start theme submission phase for next round
            await self.start_theme_submission_phase(db, round_obj, target_channel)

    async def start_theme_submission_phase(self, db, completed_round, target_channel):
        """Start the theme submission phase after a round is completed."""
        # Get guild settings
        guild_id = str(completed_round.guild_id)
        guild = await db.get_or_create_guild(guild_id)
        
        # Calculate theme submission and voting periods
        now = datetime.datetime.utcnow()
        theme_submission_end = now + datetime.timedelta(days=guild.theme_submission_days)
        theme_voting_end = theme_submission_end + datetime.timedelta(days=guild.theme_voting_days)
        
        # Update the completed round with theme submission timings
        await db.update_round_theme_timing(
            completed_round.id,
            theme_submission_end=theme_submission_end,
            theme_voting_end=theme_voting_end
        )
        
        # Create theme submission announcement
        embed = discord.Embed(
            title="🎭 Theme Suggestion Phase",
            description=f"Round #{completed_round.round_number} is complete! Now suggest themes for the next round.",
            color=discord.Color.purple(),
        )
        
        embed.add_field(
            name="How to Submit",
            value="Use `/submit_theme` to suggest a theme for the next round!",
            inline=False,
        )
        
        embed.add_field(
            name="Theme Submission Deadline",
            value=f"<t:{int(theme_submission_end.timestamp())}:F> (<t:{int(theme_submission_end.timestamp())}:R>)",
            inline=False,
        )
        
        embed.add_field(
            name="Theme Voting Deadline",
            value=f"<t:{int(theme_voting_end.timestamp())}:F> (<t:{int(theme_voting_end.timestamp())}:R>)",
            inline=False,
        )
        
        # Send the theme submission announcement
        if target_channel:
            try:
                theme_message = await target_channel.send(embed=embed)
                await db.update_round_theme_message_ids(
                    completed_round.id, theme_submission_message_id=str(theme_message.id)
                )
            except Exception as e:
                print(f"Error sending theme submission message: {e}")

    async def start_theme_voting_phase(self, db, round_obj):
        """Start the theme voting phase using emoji reactions."""
        # Get guild info
        discord_guild_id, channel_id, _ = await db.get_round_guild_info(round_obj.id)
        if not discord_guild_id:
            return

        guild = self.bot.get_guild(int(discord_guild_id))
        if not guild:
            return

        # Get theme submissions
        theme_submissions = await db.get_round_theme_submissions(round_obj.id)
        
        if not theme_submissions:
            # No theme submissions, skip theme voting
            return

        # Check if we have too many theme submissions for our emoji set
        if len(theme_submissions) > len(VOTING_EMOJIS):
            # Truncate to available emojis
            theme_submissions = theme_submissions[:len(VOTING_EMOJIS)]

        # Find the target channel
        target_channel = None
        if channel_id:
            target_channel = guild.get_channel(int(channel_id))
            if (
                target_channel
                and not target_channel.permissions_for(guild.me).send_messages
            ):
                target_channel = None

        if not target_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        # If we found a valid channel, send the theme voting message
        if target_channel:
            try:
                # Send a header message for theme voting
                main_content = f"# 🎭 Theme Voting for Next Round\n\n"
                main_content += f"Vote for your favorite theme suggestions using the emoji reactions below!\n"
                main_content += f"You can vote for up to 3 themes.\n\n"
                
                # Send the main voting message
                voting_message = await target_channel.send(
                    main_content, allowed_mentions=discord.AllowedMentions.none()
                )
                
                # Send detailed theme submission info in follow-up messages
                for idx, theme_submission in enumerate(theme_submissions):
                    detail_entry = self._format_theme_voting_detail(idx, theme_submission)
                    await target_channel.send(
                        detail_entry, allowed_mentions=discord.AllowedMentions.none()
                    )

                # Add emoji reactions for each theme submission
                for idx, theme_submission in enumerate(theme_submissions):
                    emoji = VOTING_EMOJIS[idx]
                    try:
                        await voting_message.add_reaction(emoji)
                    except discord.HTTPException:
                        pass

                # Save the theme voting message ID
                await db.update_round_theme_message_ids(
                    round_obj.id, theme_voting_message_id=str(voting_message.id)
                )

            except Exception as e:
                await target_channel.send(
                    f"Error creating theme voting message: {e}"
                )

    def _format_theme_voting_detail(self, theme_index, theme_submission):
        """Format detailed theme submission information for voting messages."""
        emoji = VOTING_EMOJIS[theme_index] if theme_index < len(VOTING_EMOJIS) else "📌"
        detail = f"{emoji} **Theme #{theme_index + 1}**: {theme_submission.theme_text}\n"
        if theme_submission.description:
            detail += f"*{theme_submission.description}*\n"
        detail += "\n"
        return detail

    async def complete_theme_voting(self, db, round_obj):
        """Complete theme voting and select the winning theme for the next round."""
        # Get guild info
        discord_guild_id, channel_id, _ = await db.get_round_guild_info(round_obj.id)
        if not discord_guild_id:
            return

        guild = self.bot.get_guild(int(discord_guild_id))
        if not guild:
            return

        # Get theme submissions
        theme_submissions = await db.get_round_theme_submissions(round_obj.id)
        
        # Count emoji reactions if we have a theme voting message
        if round_obj.theme_voting_message_id:
            voting_message = None
            
            # Try to find the theme voting message
            if channel_id:
                target_channel = guild.get_channel(int(channel_id))
                if target_channel:
                    try:
                        voting_message = await target_channel.fetch_message(
                            int(round_obj.theme_voting_message_id)
                        )
                    except Exception:
                        pass

            # If not found in dedicated channel, search all channels
            if not voting_message:
                for channel in guild.text_channels:
                    try:
                        voting_message = await channel.fetch_message(
                            int(round_obj.theme_voting_message_id)
                        )
                        break
                    except Exception:
                        continue

            # Count reactions for each theme submission
            if voting_message:
                for idx, theme_submission in enumerate(theme_submissions):
                    if idx < len(VOTING_EMOJIS):
                        emoji = VOTING_EMOJIS[idx]
                        reaction = discord.utils.get(voting_message.reactions, emoji=emoji)
                        if reaction:
                            vote_count = max(0, reaction.count - 1)
                            theme_submission.votes_received = vote_count
                        else:
                            theme_submission.votes_received = 0
                    else:
                        theme_submission.votes_received = 0

                await db.session.commit()

        # Calculate theme voting results
        theme_results = await db.calculate_theme_voting_results(round_obj.id)
        
        # Select the winning theme (most votes)
        winning_theme = "General Music"  # Default theme
        if theme_results:
            winner = theme_results[0]  # First in sorted list (highest votes)
            winning_theme = winner[1].theme_text  # theme_submission.theme_text
        
        # Find target channel for announcement
        target_channel = None
        if channel_id:
            target_channel = guild.get_channel(int(channel_id))
            if (
                target_channel
                and not target_channel.permissions_for(guild.me).send_messages
            ):
                target_channel = None

        if not target_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        # Announce the winning theme
        if target_channel:
            embed = discord.Embed(
                title="🎭 Theme Voting Results",
                description=f"The theme for the next round has been decided!",
                color=discord.Color.green(),
            )
            
            embed.add_field(
                name="Winning Theme",
                value=f"**{winning_theme}**",
                inline=False,
            )
            
            if theme_results:
                results_text = ""
                for idx, (player, theme_submission, _, votes) in enumerate(theme_results[:3]):
                    username = await self._get_username(player.user_id)
                    position = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"#{idx + 1}"
                    results_text += f"{position} {theme_submission.theme_text} - {votes} votes (by {username})\n"
                
                embed.add_field(
                    name="Top Theme Suggestions",
                    value=results_text,
                    inline=False,
                )
            
            embed.add_field(
                name="What's Next?",
                value="Use `/start` to begin the next round with the winning theme!",
                inline=False,
            )
            
            await target_channel.send(embed=embed)

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
        name="submit_theme", description="Submit a theme suggestion for the next round"
    )
    async def submit_theme(self, interaction: discord.Interaction):
        """Submit a theme suggestion for the next round."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)

            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))

            if not active_round:
                await interaction.response.send_message(
                    "There's no active round! Theme submissions happen after rounds are completed.",
                    ephemeral=True,
                )
                return

            if not active_round.is_completed:
                await interaction.response.send_message(
                    "The current round is still ongoing! Theme submissions start after the round is completed.",
                    ephemeral=True,
                )
                return

            # Check if we're in the theme submission period
            now = datetime.datetime.utcnow()
            if not active_round.theme_submission_end:
                await interaction.response.send_message(
                    "Theme submission phase hasn't started yet.",
                    ephemeral=True,
                )
                return

            if now >= active_round.theme_submission_end:
                if active_round.theme_voting_end and now < active_round.theme_voting_end:
                    await interaction.response.send_message(
                        f"Theme submission period has ended! Theme voting is now open until <t:{int(active_round.theme_voting_end.timestamp())}:F>",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"Theme submission and voting periods have ended. Wait for the next round!",
                        ephemeral=True,
                    )
                return

            # Show theme submission modal
            modal = ThemeSubmissionModal(db, str(interaction.guild_id))
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
