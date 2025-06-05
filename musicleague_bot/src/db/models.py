import os
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, create_engine, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import relationship, sessionmaker
import datetime

# Create the base class for declarative models
Base = declarative_base()

class Guild(Base):
    """Model representing a Discord server/guild."""
    __tablename__ = "guilds"
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False)
    submission_days = Column(Integer, default=3)
    voting_days = Column(Integer, default=3)
    active_round = Column(Integer, nullable=True)
    channel_id = Column(String, nullable=True)  # Dedicated channel for Music League
    
    # Relationships
    rounds = relationship("Round", back_populates="guild", cascade="all, delete-orphan")
    players = relationship("Player", back_populates="guild", cascade="all, delete-orphan")
    
class Player(Base):
    """Model representing a player in the Music League."""
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    total_score = Column(Integer, default=0)
    
    # Relationships
    guild = relationship("Guild", back_populates="players")
    submissions = relationship("Submission", back_populates="player", cascade="all, delete-orphan")

class Round(Base):
    """Model representing a round in the Music League."""
    __tablename__ = "rounds"
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    theme = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    submission_end = Column(DateTime, nullable=False)
    voting_end = Column(DateTime, nullable=False)
    is_completed = Column(Boolean, default=False)
    submission_message_id = Column(String, nullable=True)
    voting_message_id = Column(String, nullable=True)
    results_message_id = Column(String, nullable=True)
    
    # Relationships
    guild = relationship("Guild", back_populates="rounds")
    submissions = relationship("Submission", back_populates="round", cascade="all, delete-orphan")

class Submission(Base):
    """Model representing a music submission in a round."""
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    content = Column(String, nullable=False)
    description = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    votes_received = Column(Integer, default=0)
    
    # Relationships
    round = relationship("Round", back_populates="submissions")
    player = relationship("Player", back_populates="submissions")

# Create async engine factory function
def get_engine():
    """Create and return a SQLAlchemy engine."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///musicleague.db")
    if database_url.startswith("sqlite:"):
        database_url = database_url.replace("sqlite:", "sqlite+aiosqlite:")
    
    return create_async_engine(database_url, echo=True)

# Create session factory
async def get_session():
    """Create and return a SQLAlchemy session."""
    engine = get_engine()
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return async_session()

# Function to create all tables
async def init_db():
    """Initialize the database by creating all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
