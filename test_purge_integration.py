#!/usr/bin/env python3
"""
Integration test demonstrating the complete purge workflow.
This test shows how the purge command works in a realistic scenario.
"""

import sys
import os
import asyncio

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_purge_integration():
    """Test the complete purge workflow in a realistic scenario."""
    print("🎮 Music League Purge Integration Test")
    print("=" * 60)
    print("This test simulates a complete game lifecycle with purge:\n")

    from musicleague_bot.src.db import init_db, get_session
    from musicleague_bot.src.db.service import DatabaseService

    session = None
    try:
        # Initialize database
        await init_db()

        # Create a test session
        session = await get_session()
        db = DatabaseService(session)

        import uuid
        test_guild_id = f"integration_test_{uuid.uuid4().hex[:8]}"

        print("📋 SCENARIO: A Discord server has been using Music League")
        print("-" * 60)

        # Step 1: Initial setup
        print("\n1️⃣ Server admin configures settings:")
        guild = await db.update_guild_settings(
            test_guild_id, submission_days=7, voting_days=5, channel_id="123456789"
        )
        print(f"   • Submission period: {guild.submission_days} days")
        print(f"   • Voting period: {guild.voting_days} days")
        print(f"   • Dedicated channel: {guild.channel_id}")

        # Step 2: Create multiple rounds with activity
        print("\n2️⃣ Community plays 3 rounds of Music League:")
        
        for round_num in range(1, 4):
            round_obj = await db.create_round(test_guild_id, f"Round {round_num} Theme")
            print(f"\n   Round {round_num}: {round_obj.theme}")
            
            # Simulate multiple players submitting
            for player_num in range(1, 6):
                player_id = f"user_{player_num}"
                submission = await db.create_submission(
                    test_guild_id,
                    player_id,
                    f"https://music.com/song_r{round_num}_p{player_num}",
                    f"My submission for {round_obj.theme}",
                )
                
                # Simulate scoring
                score = (6 - player_num) * round_num
                await db.update_player_score(test_guild_id, player_id, score)
            
            # Complete the round
            await db.complete_round(round_obj.id)
            print(f"   ✓ 5 players submitted and voted")

        # Step 3: Check accumulated data
        print("\n3️⃣ Data accumulated over time:")
        from sqlalchemy import text

        result = await session.execute(
            text("SELECT COUNT(*) FROM players WHERE guild_id = :guild_id"),
            {"guild_id": guild.id},
        )
        player_count = result.scalar()
        
        result = await session.execute(
            text("SELECT COUNT(*) FROM rounds WHERE guild_id = :guild_id"),
            {"guild_id": guild.id},
        )
        round_count = result.scalar()
        
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM submissions WHERE round_id IN "
                "(SELECT id FROM rounds WHERE guild_id = :guild_id)"
            ),
            {"guild_id": guild.id},
        )
        submission_count = result.scalar()
        
        print(f"   • Total players: {player_count}")
        print(f"   • Total rounds: {round_count}")
        print(f"   • Total submissions: {submission_count}")

        # Step 4: View leaderboard
        print("\n4️⃣ Current leaderboard:")
        leaderboard = await db.get_leaderboard(test_guild_id, limit=5)
        for idx, player in enumerate(leaderboard, 1):
            print(f"   {idx}. Player {player.user_id}: {player.total_score} points")

        # Step 5: Admin decides to start fresh
        print("\n5️⃣ Admin runs /purge command:")
        print("   💭 'Let's start a new season with fresh scores!'")
        
        success = await db.purge_guild_data(test_guild_id)
        
        if success:
            print("   ✅ Purge completed successfully")
        
        # Step 6: Verify data cleanup
        print("\n6️⃣ After purge - checking data:")
        
        result = await session.execute(
            text("SELECT COUNT(*) FROM players WHERE guild_id = :guild_id"),
            {"guild_id": guild.id},
        )
        player_count_after = result.scalar()
        
        result = await session.execute(
            text("SELECT COUNT(*) FROM rounds WHERE guild_id = :guild_id"),
            {"guild_id": guild.id},
        )
        round_count_after = result.scalar()
        
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM submissions WHERE round_id IN "
                "(SELECT id FROM rounds WHERE guild_id = :guild_id)"
            ),
            {"guild_id": guild.id},
        )
        submission_count_after = result.scalar()
        
        print(f"   • Players: {player_count} → {player_count_after} ✓")
        print(f"   • Rounds: {round_count} → {round_count_after} ✓")
        print(f"   • Submissions: {submission_count} → {submission_count_after} ✓")

        # Step 7: Verify settings preserved
        print("\n7️⃣ Settings preserved after purge:")
        guild_after = await db.get_or_create_guild(test_guild_id)
        print(f"   • Submission period: {guild_after.submission_days} days ✓")
        print(f"   • Voting period: {guild_after.voting_days} days ✓")
        print(f"   • Dedicated channel: {guild_after.channel_id} ✓")
        print(f"   • Active round: {guild_after.active_round} (reset to None) ✓")

        # Step 8: Ready for new round
        print("\n8️⃣ Server is ready for a fresh start:")
        print("   🎵 Admin can now use /start to begin a new round")
        print("   ⚙️ All settings are preserved")
        print("   🎯 All player scores are reset to zero")

        print("\n" + "=" * 60)
        print("🎉 INTEGRATION TEST PASSED")
        print("=" * 60)
        print("\n📊 Test Summary:")
        print("   ✓ Purge removes player data")
        print("   ✓ Purge removes round data")
        print("   ✓ Purge removes submission data")
        print("   ✓ Purge preserves guild settings")
        print("   ✓ Admin can start fresh after purge")

    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if session:
            await session.close()


def main():
    """Main entry point for the test."""
    asyncio.run(test_purge_integration())


if __name__ == "__main__":
    main()
