#!/usr/bin/env python3
"""
End-to-end test demonstrating the check_submission command workflow.
This simulates the user experience of submitting music and then checking their submission.
"""

import asyncio
import datetime
import sys
import os

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from musicleague_bot.src.db import DatabaseService, get_session, init_db


async def test_user_workflow():
    """Test the complete user workflow: round creation -> submission -> check submission."""
    print("🎵 Testing Music League Bot User Workflow...")
    print("=" * 60)
    
    # Initialize database
    await init_db()
    
    # Test data simulating Discord guild and users
    GUILD_ID = "987654321"
    USER_ALICE = "123456"
    USER_BOB = "789012"
    
    # Get a database session
    session = await get_session()
    db = DatabaseService(session)
    
    try:
        print("🏗️  Step 1: Admin creates a new round...")
        round_obj = await db.create_round(GUILD_ID, "Songs that make you nostalgic")
        print(f"   ✅ Round #{round_obj.round_number} created with theme: '{round_obj.theme}'")
        print(f"   📅 Submission deadline: {round_obj.submission_end}")
        print(f"   🗳️  Voting deadline: {round_obj.voting_end}")
        
        print("\n👤 Step 2: Alice tries to check submission before submitting...")
        alice_submission = await db.get_user_submission(GUILD_ID, USER_ALICE)
        if alice_submission is None:
            print("   ✅ Correctly returns None - Alice hasn't submitted yet")
        else:
            print("   ❌ ERROR: Expected None but got submission")
            return False
        
        print("\n🎵 Step 3: Alice submits her favorite nostalgic song...")
        alice_content = "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        alice_description = "This song always reminds me of summer road trips with my family"
        
        created_submission = await db.create_submission(
            GUILD_ID, USER_ALICE, alice_content, alice_description
        )
        print(f"   ✅ Alice's submission recorded: {alice_content}")
        print(f"   📝 Description: {alice_description}")
        
        print("\n🔍 Step 4: Alice checks her submission...")
        retrieved_submission = await db.get_user_submission(GUILD_ID, USER_ALICE)
        
        if retrieved_submission is None:
            print("   ❌ ERROR: Alice's submission not found")
            return False
        
        print(f"   ✅ Alice can see her submission:")
        print(f"      🎵 Content: {retrieved_submission.content}")
        print(f"      📝 Description: {retrieved_submission.description}")
        print(f"      ⏰ Submitted at: {retrieved_submission.submitted_at}")
        
        # Verify data integrity
        if retrieved_submission.content != alice_content:
            print(f"   ❌ ERROR: Content mismatch")
            return False
        if retrieved_submission.description != alice_description:
            print(f"   ❌ ERROR: Description mismatch")
            return False
        
        print("\n🎵 Step 5: Bob also submits a song...")
        bob_content = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        bob_description = "Classic tune that never gets old!"
        
        await db.create_submission(GUILD_ID, USER_BOB, bob_content, bob_description)
        print(f"   ✅ Bob's submission recorded: {bob_content}")
        
        print("\n🔍 Step 6: Bob checks his submission...")
        bob_submission = await db.get_user_submission(GUILD_ID, USER_BOB)
        
        if bob_submission is None:
            print("   ❌ ERROR: Bob's submission not found")
            return False
        
        print(f"   ✅ Bob can see his submission:")
        print(f"      🎵 Content: {bob_submission.content}")
        print(f"      📝 Description: {bob_submission.description}")
        
        print("\n🔒 Step 7: Verify user isolation - Alice can't see Bob's submission...")
        # When Alice checks, she should only see her own submission
        alice_check_again = await db.get_user_submission(GUILD_ID, USER_ALICE)
        
        if alice_check_again.content == alice_content and alice_check_again.content != bob_content:
            print("   ✅ User isolation working - Alice only sees her own submission")
        else:
            print("   ❌ ERROR: User isolation failed")
            return False
        
        print("\n📊 Step 8: Verify round has multiple submissions...")
        all_submissions = await db.get_round_submissions(round_obj.id)
        print(f"   ✅ Round has {len(all_submissions)} submissions total")
        
        if len(all_submissions) != 2:
            print(f"   ❌ ERROR: Expected 2 submissions, got {len(all_submissions)}")
            return False
        
        print("\n🎉 WORKFLOW TEST PASSED!")
        print("=" * 60)
        print("Summary of what was tested:")
        print("✓ Users can check submission status before submitting (returns None)")
        print("✓ Users can successfully submit songs with descriptions")
        print("✓ Users can check their submission after submitting")
        print("✓ Users only see their own submissions (privacy)")
        print("✓ Multiple users can submit to the same round")
        print("✓ Data integrity is maintained throughout")
        
        return True
        
    except Exception as e:
        print(f"❌ WORKFLOW TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await session.close()


async def main():
    success = await test_user_workflow()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)