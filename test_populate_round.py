#!/usr/bin/env python3
"""
Test script that creates a new round and populates it with more than 10 submissions.
This script can be used to test the bot's handling of rounds with many submissions.
"""

import sys
import os
import asyncio
import random
from datetime import datetime, timedelta

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from musicleague_bot.src.db import get_session, init_db
from musicleague_bot.src.db.service import DatabaseService
from musicleague_bot.src.db.models import Guild, Player, Round, Submission

# Test data
TEST_GUILD_ID = "1157111607663538206"  # Fake Discord guild ID
THEME = "Test Round with Many Submissions"
USER_IDS = [
    "111111111111111111",  # Fake Discord user IDs
    "222222222222222222",
    "333333333333333333",
    "444444444444444444",
    "555555555555555555",
]

# Test song submissions - a mix of real and fictional tracks
TEST_SUBMISSIONS = [
    {
        "content": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
        "description": "This is a classic rock song with amazing guitar solos"
    },
    {
        "content": "https://open.spotify.com/track/0KXO7MwVOuzvMTnSUvwDl0",
        "description": "A relaxing indie track perfect for rainy days"
    },
    {
        "content": "https://open.spotify.com/track/5GorCbAP4aL0EJ16frG2hd",
        "description": "Upbeat pop song that always gets me energized"
    },
    {
        "content": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
        "description": "Nostalgic 80s hit that never gets old"
    },
    {
        "content": "https://open.spotify.com/track/1BxfuPKGuaTgP7aM0Bbdwr",
        "description": "Jazz fusion with intricate drum patterns"
    },
    {
        "content": "https://open.spotify.com/track/3MjUtNVVq3C8Fn0MP3zhXa",
        "description": "Alternative rock with meaningful lyrics"
    },
    {
        "content": "https://open.spotify.com/track/6DCZcSspjsKoFjzjrWoCdn",
        "description": "Electronic dance music with a unique drop"
    },
    {
        "content": "https://open.spotify.com/track/5ChkMS8OtdzJeqyybCc9R5",
        "description": "Folk song with beautiful harmonies"
    },
    {
        "content": "https://open.spotify.com/track/2takcwOaAZWiXQijPHIx7B",
        "description": "Hip-hop track with clever wordplay"
    },
    {
        "content": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b",
        "description": "Progressive metal with technical guitar work"
    },
    {
        "content": "https://open.spotify.com/track/06KyNuuMOX1ROXRhj787tj",
        "description": "Ambient music perfect for focusing"
    },
    {
        "content": "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3",
        "description": "Current pop hit with catchy chorus"
    },
    {
        "content": "Rick Astley - Never Gonna Give You Up",
        "description": "You know what this is!"
    },
    {
        "content": "The Beatles - Here Comes the Sun",
        "description": "Classic tune from the best band ever"
    },
    {
        "content": "Pink Floyd - Comfortably Numb",
        "description": "Epic guitar solo that changed rock history"
    },
]

async def run_test():
    """Create a test round and populate it with submissions."""
    print("🔄 Initializing database...")
    await init_db()
    
    # Get a database session
    session = await get_session()
    db = DatabaseService(session)
    
    try:
        print(f"🏗️  Creating test guild with ID: {TEST_GUILD_ID}")
        # Create or get test guild
        guild = await db.get_or_create_guild(TEST_GUILD_ID)
        
        # Set guild settings
        guild = await db.update_guild_settings(
            guild_id=TEST_GUILD_ID,
            submission_days=3,
            voting_days=4,
            channel_id="987654321098765432"  # Fake channel ID
        )
        
        print(f"🆕 Starting new round with theme: \"{THEME}\"")
        # Create a new round
        new_round = await db.create_round(TEST_GUILD_ID, THEME)
        print(f"📅 Round #{new_round.round_number} created!")
        print(f"⏰ Submission period ends: {new_round.submission_end}")
        print(f"⏰ Voting period ends: {new_round.voting_end}")
        
        # Create test players if they don't exist
        players = []
        for user_id in USER_IDS:
            print(f"👤 Creating player with user ID: {user_id}")
            player = await db.get_or_create_player(TEST_GUILD_ID, user_id)
            players.append(player)
        
        # Add multiple submissions from different players
        print("\n📝 Adding submissions to round...")
        submission_count = 0
        
        # First, give one submission to each player
        for idx, player in enumerate(players):
            if idx < len(TEST_SUBMISSIONS):
                submission_data = TEST_SUBMISSIONS[idx]
                
                # Override the active round check by directly creating a submission
                submission = Submission(
                    round_id=new_round.id,
                    player_id=player.id,
                    content=submission_data["content"],
                    description=submission_data["description"],
                    submitted_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 60))
                )
                
                session.add(submission)
                submission_count += 1
                print(f"  ✅ Added submission #{submission_count} from player {player.user_id}")
        
        # Add remaining submissions distributed randomly among players
        remaining_submissions = TEST_SUBMISSIONS[len(players):]
        for submission_data in remaining_submissions:
            # Pick a random player
            player = random.choice(players)
            
            # Create submission
            submission = Submission(
                round_id=new_round.id,
                player_id=player.id,
                content=submission_data["content"],
                description=submission_data["description"],
                submitted_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 60))
            )
            
            session.add(submission)
            submission_count += 1
            print(f"  ✅ Added submission #{submission_count} from player {player.user_id}")
        
        # Commit all changes
        await session.commit()
        
        # Verify the submissions were added
        submissions = await db.get_round_submissions(new_round.id)
        
        print(f"\n✨ Successfully created round with {len(submissions)} submissions!")
        print(f"🔍 Round ID: {new_round.id}")
        print(f"🎵 Theme: {new_round.theme}")
        print(f"📊 Submissions per player:")
        
        # Count submissions per player
        player_counts = {}
        for sub in submissions:
            player_id = sub.player_id
            if player_id in player_counts:
                player_counts[player_id] += 1
            else:
                player_counts[player_id] = 1
        
        for player in players:
            count = player_counts.get(player.id, 0)
            print(f"  Player {player.user_id}: {count} submission(s)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.close()
        print("\n🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(run_test())
