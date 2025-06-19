from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.future import select
from datetime import datetime, timedelta
from .models import Guild, Player, Round, Submission


class DatabaseService:
    """Service class to handle all database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Guild operations
    async def get_or_create_guild(self, guild_id: str) -> Guild:
        """Get a guild by Discord ID or create it if it doesn't exist."""
        query = select(Guild).where(Guild.guild_id == str(guild_id))
        result = await self.session.execute(query)
        guild = result.scalars().first()

        if not guild:
            guild = Guild(guild_id=str(guild_id))
            self.session.add(guild)
            await self.session.commit()

        return guild

    async def update_guild_settings(
        self,
        guild_id: str,
        submission_days: int = None,
        voting_days: int = None,
        channel_id: str = None,
        reminder_role_id: str = None,
    ) -> Guild:
        """Update the settings for a guild."""
        guild = await self.get_or_create_guild(guild_id)

        if submission_days is not None:
            guild.submission_days = submission_days

        if voting_days is not None:
            guild.voting_days = voting_days

        if channel_id is not None:
            guild.channel_id = channel_id

        if reminder_role_id is not None:
            guild.reminder_role_id = reminder_role_id

        await self.session.commit()
        return guild

    async def set_active_round(self, guild_id: str, round_id: int = None) -> Guild:
        """Set the active round for a guild."""
        guild = await self.get_or_create_guild(guild_id)
        guild.active_round = round_id
        await self.session.commit()
        return guild

    # Player operations
    async def get_or_create_player(self, guild_id: str, user_id: str) -> Player:
        """Get a player by Discord user ID or create if not exists."""
        guild = await self.get_or_create_guild(guild_id)

        query = select(Player).where(
            Player.guild_id == guild.id, Player.user_id == str(user_id)
        )
        result = await self.session.execute(query)
        player = result.scalars().first()

        if not player:
            player = Player(user_id=str(user_id), guild_id=guild.id)
            self.session.add(player)
            await self.session.commit()

        return player

    async def update_player_score(
        self, guild_id: str, user_id: str, score_to_add: int
    ) -> Player:
        """Update a player's score."""
        player = await self.get_or_create_player(guild_id, user_id)
        player.total_score += score_to_add
        await self.session.commit()
        return player

    async def get_leaderboard(self, guild_id: str, limit: int = 5) -> list[Player]:
        """Get the top players for a guild."""
        guild = await self.get_or_create_guild(guild_id)

        query = (
            select(Player)
            .where(Player.guild_id == guild.id)
            .order_by(Player.total_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    # Round operations
    async def create_round(self, guild_id: str, theme: str) -> Round:
        """Create a new round for the guild with the provided theme."""
        guild = await self.get_or_create_guild(guild_id)

        # Get the highest round number for the guild
        query = select(func.max(Round.round_number)).where(Round.guild_id == guild.id)
        result = await self.session.execute(query)
        highest_round = result.scalar() or 0
        new_round_number = highest_round + 1

        # Calculate end times based on guild settings
        submission_end = datetime.utcnow() + timedelta(days=guild.submission_days)
        voting_end = submission_end + timedelta(days=guild.voting_days)

        # Ensure theme is properly set
        theme = theme.strip() if theme else "General Music"

        new_round = Round(
            guild_id=guild.id,
            round_number=new_round_number,
            theme=theme,
            submission_end=submission_end,
            voting_end=voting_end,
        )

        self.session.add(new_round)
        await self.session.commit()

        # Set as active round
        await self.set_active_round(guild_id, new_round.id)

        return new_round

    async def get_round(self, round_id: int) -> Round:
        """Get a round by ID."""
        query = select(Round).where(Round.id == round_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_active_round(self, guild_id: str) -> Round:
        """Get the active round for a guild."""
        guild = await self.get_or_create_guild(guild_id)

        if not guild.active_round:
            return None

        return await self.get_round(guild.active_round)

    async def complete_round(
        self, round_id: int, results_message_id: str = None
    ) -> Round:
        """Mark a round as completed."""
        round_obj = await self.get_round(round_id)
        round_obj.is_completed = True

        if results_message_id:
            round_obj.results_message_id = results_message_id

        await self.session.commit()
        return round_obj

    async def update_round_message_ids(
        self,
        round_id: int,
        submission_message_id: str = None,
        voting_message_id: str = None,
    ) -> Round:
        """Update message IDs for a round."""
        round_obj = await self.get_round(round_id)

        if submission_message_id:
            round_obj.submission_message_id = submission_message_id

        if voting_message_id:
            round_obj.voting_message_id = voting_message_id

        await self.session.commit()
        return round_obj

    async def update_round_timing(
        self,
        round_id: int,
        submission_end: datetime = None,
        voting_end: datetime = None,
    ) -> Round:
        """Update the timing for a round's submission or voting period."""
        round_obj = await self.get_round(round_id)

        if submission_end:
            round_obj.submission_end = submission_end

        if voting_end:
            round_obj.voting_end = voting_end

        await self.session.commit()
        return round_obj

    async def get_round_guild_info(self, round_id: int) -> tuple:
        """Get the Discord guild ID and channel ID for a round without lazy loading."""
        from sqlalchemy import text

        # Use a direct SQL query to avoid lazy loading issues
        query = text(
            """
            SELECT g.guild_id, g.channel_id, g.voting_days, g.reminder_role_id
            FROM guilds g
            JOIN rounds r ON r.guild_id = g.id
            WHERE r.id = :round_id
        """
        )

        result = await self.session.execute(query, {"round_id": round_id})
        row = result.first()

        if not row:
            return None, None, None, None

        return row[0], row[1], row[2], row[3]  # guild_discord_id, channel_id, voting_days, reminder_role_id

    async def update_round_reminder_status(
        self,
        round_id: int,
        submission_reminder_sent: bool = None,
        voting_reminder_sent: bool = None,
    ) -> Round:
        """Update the reminder status for a round."""
        round_obj = await self.get_round(round_id)

        if submission_reminder_sent is not None:
            round_obj.submission_reminder_sent = submission_reminder_sent

        if voting_reminder_sent is not None:
            round_obj.voting_reminder_sent = voting_reminder_sent

        await self.session.commit()
        return round_obj

    # Submission operations
    async def create_submission(
        self, guild_id: str, user_id: str, content: str, description: str = None
    ) -> Submission:
        """Create a new submission for the active round."""
        player = await self.get_or_create_player(guild_id, user_id)
        round_obj = await self.get_active_round(guild_id)

        if not round_obj:
            return None

        # Check if player already submitted in this round
        query = select(Submission).where(
            Submission.round_id == round_obj.id, Submission.player_id == player.id
        )
        result = await self.session.execute(query)
        existing_submission = result.scalars().first()

        if existing_submission:
            # Update existing submission
            existing_submission.content = content
            existing_submission.description = description
            existing_submission.submitted_at = datetime.utcnow()
            await self.session.commit()
            return existing_submission

        # Create new submission
        submission = Submission(
            round_id=round_obj.id,
            player_id=player.id,
            content=content,
            description=description,
        )

        self.session.add(submission)
        await self.session.commit()
        return submission

    async def get_round_submissions(self, round_id: int) -> list[Submission]:
        """Get all submissions for a round."""
        query = select(Submission).where(Submission.round_id == round_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def calculate_round_results(self, round_id: int) -> list[tuple]:
        """Calculate the results for a round and update player scores."""
        # Get all submissions for the round
        submissions = await self.get_round_submissions(round_id)

        results = []
        for idx, submission in enumerate(submissions):
            # Get the player
            query = select(Player).where(Player.id == submission.player_id)
            result = await self.session.execute(query)
            player = result.scalars().first()

            # Update player score
            player.total_score += submission.votes_received

            # Add to results
            results.append((player, submission, idx, submission.votes_received))

        await self.session.commit()

        # Sort results by votes (highest first)
        results.sort(key=lambda x: x[3], reverse=True)
        return results
