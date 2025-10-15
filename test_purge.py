#!/usr/bin/env python3
"""
Test for the purge command functionality.
"""

import sys
import os
import asyncio

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_purge():
    """Test the purge functionality."""
    print("🧪 Testing purge command functionality...\n")

    from musicleague_bot.src.db import init_db, get_session
    from musicleague_bot.src.db.service import DatabaseService
    from musicleague_bot.src.db.models import Guild, Player, Round, Submission

    session = None
    try:
        # Initialize database
        await init_db()
        print("1. Database initialized")

        # Create a test session
        session = await get_session()
        db = DatabaseService(session)

        # Test guild ID
        import uuid
        test_guild_id = f"test_guild_{uuid.uuid4().hex[:8]}"

        # Create test data
        print("2. Creating test data...")
        guild = await db.get_or_create_guild(test_guild_id)
        guild_db_id = guild.id
        
        # Update settings
        await db.update_guild_settings(
            test_guild_id, submission_days=5, voting_days=4
        )
        
        # Create a round
        round_obj = await db.create_round(test_guild_id, "Test Theme")
        print(f"   ✓ Created round #{round_obj.round_number}")

        # Create some players
        player1 = await db.get_or_create_player(test_guild_id, "user_1")
        player2 = await db.get_or_create_player(test_guild_id, "user_2")
        print(f"   ✓ Created {2} players")

        # Create submissions
        submission1 = await db.create_submission(
            test_guild_id, "user_1", "https://music.com/song1", "Great song!"
        )
        submission2 = await db.create_submission(
            test_guild_id, "user_2", "https://music.com/song2", "Another great song!"
        )
        print(f"   ✓ Created {2} submissions")

        # Update player scores
        await db.update_player_score(test_guild_id, "user_1", 10)
        await db.update_player_score(test_guild_id, "user_2", 5)
        print(f"   ✓ Updated player scores")

        # Verify data exists
        print("3. Verifying test data exists...")
        from sqlalchemy import text

        # Check guilds
        result = await session.execute(
            text("SELECT COUNT(*) FROM guilds WHERE guild_id = :guild_id"),
            {"guild_id": test_guild_id},
        )
        guild_count = result.scalar()
        assert guild_count == 1, f"Expected 1 guild, found {guild_count}"
        print(f"   ✓ Found {guild_count} guild record")

        # Check players
        result = await session.execute(
            text("SELECT COUNT(*) FROM players WHERE guild_id = :guild_id"),
            {"guild_id": guild_db_id},
        )
        player_count = result.scalar()
        assert player_count == 2, f"Expected 2 players, found {player_count}"
        print(f"   ✓ Found {player_count} player records")

        # Check rounds
        result = await session.execute(
            text("SELECT COUNT(*) FROM rounds WHERE guild_id = :guild_id"),
            {"guild_id": guild_db_id},
        )
        round_count = result.scalar()
        assert round_count == 1, f"Expected 1 round, found {round_count}"
        print(f"   ✓ Found {round_count} round record")

        # Check submissions
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM submissions WHERE round_id IN "
                "(SELECT id FROM rounds WHERE guild_id = :guild_id)"
            ),
            {"guild_id": guild_db_id},
        )
        submission_count = result.scalar()
        assert submission_count == 2, f"Expected 2 submissions, found {submission_count}"
        print(f"   ✓ Found {submission_count} submission records")

        # Test purge functionality
        print("4. Testing purge functionality...")
        success = await db.purge_guild_data(test_guild_id)
        assert success, "Purge should return True"
        print("   ✓ Purge executed successfully")

        # Verify data is deleted but guild settings preserved
        print("5. Verifying data is deleted but guild settings preserved...")
        
        # Check guilds - should still exist
        result = await session.execute(
            text("SELECT COUNT(*) FROM guilds WHERE guild_id = :guild_id"),
            {"guild_id": test_guild_id},
        )
        guild_count = result.scalar()
        assert guild_count == 1, f"Expected 1 guild after purge (settings preserved), found {guild_count}"
        print(f"   ✓ Guild record preserved: {guild_count} found")
        
        # Verify settings are preserved
        result = await session.execute(
            text("SELECT submission_days, voting_days FROM guilds WHERE guild_id = :guild_id"),
            {"guild_id": test_guild_id},
        )
        settings = result.fetchone()
        assert settings[0] == 5, f"Expected submission_days=5, found {settings[0]}"
        assert settings[1] == 4, f"Expected voting_days=4, found {settings[1]}"
        print(f"   ✓ Guild settings preserved: submission_days={settings[0]}, voting_days={settings[1]}")

        # Check players
        result = await session.execute(
            text("SELECT COUNT(*) FROM players WHERE guild_id = :guild_id"),
            {"guild_id": guild_db_id},
        )
        player_count = result.scalar()
        assert player_count == 0, f"Expected 0 players after purge, found {player_count}"
        print(f"   ✓ Player records deleted: {player_count} remaining")

        # Check rounds
        result = await session.execute(
            text("SELECT COUNT(*) FROM rounds WHERE guild_id = :guild_id"),
            {"guild_id": guild_db_id},
        )
        round_count = result.scalar()
        assert round_count == 0, f"Expected 0 rounds after purge, found {round_count}"
        print(f"   ✓ Round records deleted: {round_count} remaining")

        # Check submissions (should be deleted via cascade)
        result = await session.execute(text("SELECT COUNT(*) FROM submissions"))
        submission_count = result.scalar()
        assert (
            submission_count == 0
        ), f"Expected 0 submissions after purge, found {submission_count}"
        print(f"   ✓ Submission records deleted: {submission_count} remaining")

        print("\n🎉 ALL PURGE TESTS PASSED!")
        print("\n📊 Summary:")
        print("   • Purge command successfully deletes player, round, and submission data")
        print("   • Guild record and settings are preserved after purge")
        print("   • Cascading deletes work correctly for related tables")
        print("   • Database integrity maintained after purge")

    except Exception as e:
        print(f"\n❌ PURGE TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if session:
            await session.close()


def main():
    """Main entry point for the test."""
    asyncio.run(test_purge())


if __name__ == "__main__":
    main()
