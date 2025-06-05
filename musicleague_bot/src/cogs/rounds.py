import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Modal, TextInput
import datetime
from typing import Optional, List
from ..db import DatabaseService

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
            max_length=200
        )
        
        self.description = TextInput(
            label="Description (Optional)",
            placeholder="Add context or why you chose this song",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        
        self.add_item(self.submission)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Create submission in database
        submission = await self.db_service.create_submission(
            guild_id=self.guild_id,
            user_id=str(interaction.user.id),
            content=self.submission.value,
            description=self.description.value if self.description.value else None
        )
        
        if not submission:
            await interaction.response.send_message(
                "There's no active round to submit to!", ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            f"Your submission has been recorded! Thank you for participating.", 
            ephemeral=True
        )

# No need for custom VoteView class as we'll use Discord's built-in poll feature

class RoundsCog(commands.Cog):
    """Commands for managing Music League rounds."""
    
    def __init__(self, bot):
        self.bot = bot
        self.check_rounds.start()
    
    def cog_unload(self):
        self.check_rounds.cancel()
    
    @tasks.loop(minutes=5)  # Changed from 15 to 5 minutes for faster response to manual transitions
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
                if now >= active_round.submission_end and not active_round.voting_message_id:
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
        """Start the voting phase for a round."""
        # Get guild info without lazy loading
        discord_guild_id, channel_id, voting_days = await db.get_round_guild_info(round_obj.id)
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
                if target_channel and not target_channel.permissions_for(guild.me).send_messages:
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
            
        # Create an introduction message for the poll
        intro_message = f"# 🎵 Voting for Round #{round_obj.round_number} 🎵\n\n"
        intro_message += f"Vote for your favorite submission below! Voting ends <t:{int(round_obj.voting_end.timestamp())}:R>\n\n"
        
        if round_obj.theme:
            intro_message += f"**Theme**: {round_obj.theme}\n\n"
            
        # Create options for the poll - each will be a shortened version of the submission
        poll_options = []
        submission_details = []
        
        for idx, submission in enumerate(submissions):
            # Create a short description for the poll option (max 80 chars)
            short_desc = submission.content
            if len(short_desc) > 77:  # Account for "..."
                short_desc = short_desc[:77] + "..."
            
            # Add to poll options
            poll_options.append(f"Submission #{idx + 1}: {short_desc}")
            
            # Create detailed submission text for followup message
            detail_text = f"**Submission #{idx + 1}**\n"
            detail_text += f"{submission.content}\n"
            if submission.description:
                detail_text += f"\n{submission.description}\n"
            
            submission_details.append(detail_text)
        
        # We already have the channel_id from our earlier call
        target_channel = None
        
        if channel_id:
            # Try to get the dedicated channel
            target_channel = guild.get_channel(int(channel_id))
            if target_channel and not target_channel.permissions_for(guild.me).send_messages:
                target_channel = None  # Reset if we don't have permission to send messages
                
        # If no dedicated channel or it wasn't found/accessible, find an appropriate channel
        if not target_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break
        
        # If we found a valid channel, send the poll
        if target_channel:
            try:
                # Create a Poll object
                poll = discord.Poll(
                    question="Which submission is your favorite?",
                    multiple=False,
                    duration=datetime.timedelta(days=voting_days),
                )

                for option in poll_options:
                    poll.add_answer(text=option)
                
                # Create the poll message
                poll_message = await target_channel.send(
                    content=intro_message,
                    poll=poll,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                
                # Save the poll message ID
                await db.update_round_message_ids(round_obj.id, voting_message_id=str(poll_message.id))
                
                # Send additional details about submissions
                details_message = "## Submission Details\n\n"
                details_message += "\n\n".join(submission_details)
                
                # Split into multiple messages if needed (2000 char limit)
                if len(details_message) <= 2000:
                    await target_channel.send(details_message, allowed_mentions=discord.AllowedMentions.none())
                else:
                    # Split into chunks
                    chunks = []
                    current_chunk = "## Submission Details\n\n"
                    
                    for detail in submission_details:
                        if len(current_chunk + detail + "\n\n") > 1900:
                            chunks.append(current_chunk)
                            current_chunk = detail + "\n\n"
                        else:
                            current_chunk += detail + "\n\n"
                            
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for chunk in chunks:
                        await target_channel.send(chunk, allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                # If poll creation fails, send an error message and try an alternative approach
                await target_channel.send(f"Error creating poll: {str(e)}. Please contact the bot administrator.")
    
    async def complete_round(self, db, round_obj):
        """Complete a round and calculate results."""
        # Get guild info without lazy loading
        discord_guild_id, channel_id, _ = await db.get_round_guild_info(round_obj.id)
        if not discord_guild_id:
            return  # Couldn't find guild info
            
        guild = self.bot.get_guild(int(discord_guild_id))
        if not guild:
            return  # Bot might have left the guild
        
        # Get submissions
        submissions = await db.get_round_submissions(round_obj.id)
        
        # Try to get the poll results if available
        poll_data = {}
        if round_obj.voting_message_id:
            # We already have the channel_id from our earlier call
            if channel_id:
                target_channel = guild.get_channel(int(channel_id))
                if target_channel:
                    try:
                        # Try to get the poll from the dedicated channel first
                        poll_message = await target_channel.fetch_message(int(round_obj.voting_message_id))
                        
                        # Process poll data if found
                        if hasattr(poll_message, 'poll') and poll_message.poll:
                            # Extract vote counts
                            for idx, answer in enumerate(poll_message.poll.answers):
                                if idx < len(submissions):
                                    # Update submissions with vote counts
                                    submission = submissions[idx]
                                    submission.votes_received = answer.vote_count
                                    await db.session.commit()
                            # End the poll if it's still active
                            if not poll_message.poll.is_finalized():
                                await poll_message.poll.end()
                            # Poll found and processed, no need to look further
                            poll_data = True
                    except Exception as e:
                        # Message not found in dedicated channel, we'll search all channels
                        print(f"Error fetching poll message from dedicated channel: {e}")
            
            # If we didn't find the poll message in a dedicated channel, search all channels
            if not poll_data:
                for channel in guild.text_channels:
                    try:
                        # Fetch the poll message
                        poll_message = await channel.fetch_message(int(round_obj.voting_message_id))
                        
                        # Check if it has a poll
                        if hasattr(poll_message, 'poll') and poll_message.poll:
                            # Extract vote counts
                            for idx, answer in enumerate(poll_message.poll.answers):
                                if idx < len(submissions):
                                    # Update submissions with vote counts from the poll
                                    submission = submissions[idx]
                                    submission.votes_received = answer.vote_count
                                    await db.session.commit()
                            # End the poll if it's still active
                            if not poll_message.poll.is_finalized():
                                await poll_message.poll.end()
                        break
                    except Exception as e:
                        # Message not found or other error
                        print(f"Error fetching poll message: {e}")
                        pass
        
        # Calculate results
        results = await db.calculate_round_results(round_obj.id)
        
        # Create results message
        results_content = f"# 🏆 Results for Round #{round_obj.round_number} 🏆\n\n"
        results_content += "The round has ended! Here are the results:\n\n"
        
        if round_obj.theme:
            results_content += f"**Theme**: {round_obj.theme}\n\n"
        
        # Add each submission to the results with their score
        for idx, (player, submission, score) in enumerate(results):
            user = self.bot.get_user(int(player.user_id)) or await self.bot.fetch_user(int(player.user_id))
            username = user.display_name if user else f"User {player.user_id}"
            
            # Add medal emoji for top 3
            medal = ""
            if idx == 0:
                medal = "🥇 "
            elif idx == 1:
                medal = "🥈 "
            elif idx == 2:
                medal = "🥉 "
                
            results_content += f"### {medal}#{idx + 1}: {username} - {score} votes\n"
            results_content += f"{submission.content}\n"
            if submission.description:
                results_content += f"*{submission.description}*\n"
            results_content += "\n"
        
        # Add leaderboard
        leaderboard = await db.get_leaderboard(discord_guild_id, 5)
        
        results_content += "## 📊 Current Leaderboard\n\n"
        if leaderboard:
            for idx, player in enumerate(leaderboard, 1):
                user = self.bot.get_user(int(player.user_id)) or await self.bot.fetch_user(int(player.user_id))
                username = user.display_name if user else f"User {player.user_id}"
                results_content += f"#{idx}: {username} - {player.total_score} points\n"
        else:
            results_content += "No players yet!\n"
        
        # We already have the channel_id from our earlier call
        target_channel = None
        
        if channel_id:
            # Try to get the dedicated channel
            target_channel = guild.get_channel(int(channel_id))
            if target_channel and not target_channel.permissions_for(guild.me).send_messages:
                target_channel = None  # Reset if we don't have permission to send messages
                
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
                main_results = f"# 🏆 Results for Round #{round_obj.round_number} 🏆\n\n"
                main_results += "The round has ended! Here are the winners:\n\n"
                
                # Add top 3 only to main message
                for idx, (player, submission, score) in enumerate(results[:3]):
                    if idx >= 3:
                        break
                        
                    user = self.bot.get_user(int(player.user_id)) or await self.bot.fetch_user(int(player.user_id))
                    username = user.display_name if user else f"User {player.user_id}"
                    
                    medal = "🥇 " if idx == 0 else "🥈 " if idx == 1 else "🥉 "
                    main_results += f"{medal} #{idx + 1}: {username} - {score} votes\n"
                
                results_message = await target_channel.send(main_results)
                
                # Send detailed results in follow-up messages
                detailed_results = ""
                for idx, (player, submission, score) in enumerate(results):
                    user = self.bot.get_user(int(player.user_id)) or await self.bot.fetch_user(int(player.user_id))
                    username = user.display_name if user else f"User {player.user_id}"
                    
                    medal = "🥇 " if idx == 0 else "🥈 " if idx == 1 else "🥉 " if idx == 2 else ""
                    entry = f"### {medal}#{idx + 1}: {username} - {score} votes\n"
                    entry += f"{submission.content}\n"
                    if submission.description:
                        entry += f"*{submission.description}*\n"
                    entry += "\n"
                    
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
                leaderboard_msg = "## 📊 Current Leaderboard\n\n"
                if leaderboard:
                    for idx, player in enumerate(leaderboard, 1):
                        user = self.bot.get_user(int(player.user_id)) or await self.bot.fetch_user(int(player.user_id))
                        username = user.display_name if user else f"User {player.user_id}"
                        leaderboard_msg += f"#{idx}: {username} - {player.total_score} points\n"
                else:
                    leaderboard_msg += "No players yet!\n"
                
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
                    ephemeral=True
                )
                return
                
            # Validate that theme is not empty
            if not theme or theme.strip() == "":
                await interaction.response.send_message(
                    "You must provide a theme for the round. Please try again with a valid theme.",
                    ephemeral=True
                )
                return
            
            # Create new round with the required theme
            new_round = await db.create_round(str(interaction.guild_id), theme)
            
            # Create round announcement
            embed = discord.Embed(
                title=f"🎵 New Music League Round #{new_round.round_number} 🎵",
                description=f"A new round has started! Submit your music with `/submit`.",
                color=discord.Color.blue()
            )
            
            # Add theme (now required)
            embed.add_field(name="Theme", value=theme, inline=False)
            
            embed.add_field(
                name="Submission Deadline", 
                value=f"<t:{int(new_round.submission_end.timestamp())}:F> (<t:{int(new_round.submission_end.timestamp())}:R>)", 
                inline=False
            )
            
            embed.add_field(
                name="Voting Deadline", 
                value=f"<t:{int(new_round.voting_end.timestamp())}:F> (<t:{int(new_round.voting_end.timestamp())}:R>)", 
                inline=False
            )
            
            # Get guild settings
            guild = await db.get_or_create_guild(str(interaction.guild_id))
            dedicated_channel_id = guild.channel_id
            
            # Respond to the interaction first
            await interaction.response.send_message("Creating new round...", ephemeral=True)
            
            # Check if we should use a dedicated channel
            if dedicated_channel_id:
                channel = interaction.guild.get_channel(int(dedicated_channel_id))
                if channel and channel.permissions_for(interaction.guild.me).send_messages:
                    message = await channel.send(embed=embed)
                    await db.update_round_message_ids(new_round.id, submission_message_id=str(message.id))
                    
                    # Update the user's response
                    await interaction.edit_original_response(
                        content=f"Round started! Check <#{channel.id}> for details."
                    )
                    return
            
            # If no dedicated channel or couldn't send to it, send in the current channel
            message = await interaction.channel.send(embed=embed)
            await db.update_round_message_ids(new_round.id, submission_message_id=str(message.id))
            
            # Update the user's response
            await interaction.edit_original_response(
                content="Round started! See the announcement below."
            )
    
    @app_commands.command(name="submit", description="Submit a song for the current Music League round")
    async def submit(self, interaction: discord.Interaction):
        """Submit a song for the current Music League round."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)
            
            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))
            
            if not active_round:
                await interaction.response.send_message(
                    "There's no active round! Ask an admin to start a new round with `/start`", 
                    ephemeral=True
                )
                return
            
            if active_round.is_completed:
                await interaction.response.send_message(
                    "The current round is already completed! Wait for a new round to start.", 
                    ephemeral=True
                )
                return
            
            # Check if the submission period is over
            now = datetime.datetime.utcnow()
            if now >= active_round.submission_end:
                await interaction.response.send_message(
                    f"The submission period for this round has ended! Voting is now open until <t:{int(active_round.voting_end.timestamp())}:F>", 
                    ephemeral=True
                )
                return
            
            # Show submission modal
            modal = SubmissionModal(db, str(interaction.guild_id))
            await interaction.response.send_modal(modal)
    
    @app_commands.command(name="status", description="Check the status of the current Music League round")
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
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Create the status embed
            embed = discord.Embed(
                title=f"Music League Round #{active_round.round_number} Status",
                color=discord.Color.blue()
            )
            
            if active_round.theme:
                embed.add_field(name="Theme", value=active_round.theme, inline=False)
            
            now = datetime.datetime.utcnow()
            
            if now < active_round.submission_end:
                # Submission phase
                embed.add_field(
                    name="Status", 
                    value=f"Submission Phase - Submit your music with `/submit`", 
                    inline=False
                )
                
                embed.add_field(
                    name="Submission Deadline", 
                    value=f"<t:{int(active_round.submission_end.timestamp())}:F> (<t:{int(active_round.submission_end.timestamp())}:R>)", 
                    inline=False
                )
                
                # Get current submissions
                submissions = await db.get_round_submissions(active_round.id)
                embed.add_field(
                    name="Submissions", 
                    value=f"{len(submissions)} submission(s) so far", 
                    inline=False
                )
                
            elif now < active_round.voting_end:
                # Voting phase
                embed.add_field(
                    name="Status", 
                    value=f"Voting Phase - Cast your votes!", 
                    inline=False
                )
                
                embed.add_field(
                    name="Voting Deadline", 
                    value=f"<t:{int(active_round.voting_end.timestamp())}:F> (<t:{int(active_round.voting_end.timestamp())}:R>)", 
                    inline=False
                )
                
                # Get submissions
                submissions = await db.get_round_submissions(active_round.id)
                embed.add_field(
                    name="Submissions", 
                    value=f"{len(submissions)} submission(s) in this round", 
                    inline=False
                )
                
            else:
                # Completed or processing
                if active_round.is_completed:
                    embed.add_field(
                        name="Status", 
                        value=f"Round completed! Check the results message or start a new round with `/start`", 
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Status", 
                        value=f"Voting has ended - Results will be calculated soon!", 
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="end_submission", description="Forcibly end the submission period and start voting")
    @app_commands.default_permissions(administrator=True)
    async def end_submission(self, interaction: discord.Interaction):
        """Forcibly end the submission period and start the voting phase."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)
            
            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))
            
            if not active_round:
                await interaction.response.send_message(
                    "There's no active round to modify!", 
                    ephemeral=True
                )
                return
            
            # Check if we're already in voting phase or later
            now = datetime.datetime.utcnow()
            if now >= active_round.submission_end:
                await interaction.response.send_message(
                    "The submission period has already ended!", 
                    ephemeral=True
                )
                return
            
            if active_round.is_completed:
                await interaction.response.send_message(
                    "This round is already completed!", 
                    ephemeral=True
                )
                return
                
            # Get guild info to access the voting days setting
            discord_guild_id, channel_id, voting_days = await db.get_round_guild_info(active_round.id)
            if not discord_guild_id:
                await interaction.response.send_message(
                    "Error: Could not find guild settings.", 
                    ephemeral=True
                )
                return
                
            # Calculate the new voting end time based on the current time plus voting days
            now = datetime.datetime.utcnow()
            new_voting_end = now + datetime.timedelta(days=voting_days)
            
            # Update both submission end and voting end times
            await db.update_round_timing(active_round.id, submission_end=now, voting_end=new_voting_end)
            
            # We can already find the guild from interaction.guild
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "Error: Could not find the guild this round belongs to.", 
                    ephemeral=True
                )
                return
                
            # Notify the user that the submission period has ended with updated voting deadline
            await interaction.response.send_message(
                f"Submission period ended! The voting phase will begin shortly (within 5 minutes) and will end <t:{int(new_voting_end.timestamp())}:R>.",
                ephemeral=True
            )
    
    @app_commands.command(name="end_voting", description="Forcibly end the voting period and calculate results")
    @app_commands.default_permissions(administrator=True)
    async def end_voting(self, interaction: discord.Interaction):
        """Forcibly end the voting period and calculate results."""
        async with self.bot.get_db_session() as session:
            db = DatabaseService(session)
            
            # Check if there's an active round
            active_round = await db.get_active_round(str(interaction.guild_id))
            
            if not active_round:
                await interaction.response.send_message(
                    "There's no active round to modify!", 
                    ephemeral=True
                )
                return
            
            # Check if we're in voting phase
            now = datetime.datetime.utcnow()
            if now < active_round.submission_end:
                await interaction.response.send_message(
                    "The submission period hasn't ended yet! Use `/end_submission` first.", 
                    ephemeral=True
                )
                return
                
            if now >= active_round.voting_end:
                await interaction.response.send_message(
                    "The voting period has already ended!", 
                    ephemeral=True
                )
                return
            
            if active_round.is_completed:
                await interaction.response.send_message(
                    "This round is already completed!", 
                    ephemeral=True
                )
                return
                
            # Update the voting end time to now
            await db.update_round_timing(active_round.id, voting_end=now)
            
            # We can already find the guild from interaction.guild
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "Error: Could not find the guild this round belongs to.", 
                    ephemeral=True
                )
                return
            
            # Notify the user that the voting period has ended
            await interaction.response.send_message(
                "Voting period ended! Results will be calculated shortly with the next check (within 5 minutes).",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RoundsCog(bot))
