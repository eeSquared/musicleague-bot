#!/usr/bin/env python3
"""
Test for the check_submission command functionality.
"""

import asyncio
import datetime
import sys
import os

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from musicleague_bot.src.db import DatabaseService, get_session
from musicleague_bot.src.db.models import init_db


async def test_check_submission():
    """Test the get_user_submission database method."""
    print("🧪 Testing check_submission functionality...")
    
    # Initialize database
    await init_db()
    
    # Test data
    TEST_GUILD_ID = "12345"
    TEST_USER_ID = "67890" 
    TEST_CONTENT = "https://open.spotify.com/track/test123"
    TEST_DESCRIPTION = "This is my favorite song!"
    
    # Get a database session
    session = await get_session()
    db = DatabaseService(session)
    
    try:
        print("📋 Step 1: Testing with no active round...")
        submission = await db.get_user_submission(TEST_GUILD_ID, TEST_USER_ID)
        if submission is None:
            print("  ✅ PASS: No submission returned when no active round")
        else:
            print("  ❌ FAIL: Expected None but got submission")
            return False
        
        print("📋 Step 2: Creating a new round...")
        round_obj = await db.create_round(TEST_GUILD_ID, "Test Theme")
        print(f"  ✅ Created round #{round_obj.round_number}")
        
        print("📋 Step 3: Testing with active round but no submission...")
        submission = await db.get_user_submission(TEST_GUILD_ID, TEST_USER_ID)
        if submission is None:
            print("  ✅ PASS: No submission returned when user hasn't submitted")
        else:
            print("  ❌ FAIL: Expected None but got submission")
            return False
        
        print("📋 Step 4: Creating a submission...")
        created_submission = await db.create_submission(
            TEST_GUILD_ID, TEST_USER_ID, TEST_CONTENT, TEST_DESCRIPTION
        )
        print(f"  ✅ Created submission: {created_submission.content}")
        
        print("📋 Step 5: Testing get_user_submission with existing submission...")
        retrieved_submission = await db.get_user_submission(TEST_GUILD_ID, TEST_USER_ID)
        
        if retrieved_submission is None:
            print("  ❌ FAIL: Expected submission but got None")
            return False
        
        if retrieved_submission.content != TEST_CONTENT:
            print(f"  ❌ FAIL: Content mismatch. Expected '{TEST_CONTENT}', got '{retrieved_submission.content}'")
            return False
            
        if retrieved_submission.description != TEST_DESCRIPTION:
            print(f"  ❌ FAIL: Description mismatch. Expected '{TEST_DESCRIPTION}', got '{retrieved_submission.description}'")
            return False
            
        print("  ✅ PASS: Retrieved submission matches expected data")
        print(f"    Content: {retrieved_submission.content}")
        print(f"    Description: {retrieved_submission.description}")
        print(f"    Submitted at: {retrieved_submission.submitted_at}")
        
        print("📋 Step 6: Testing with different user (should return None)...")
        other_submission = await db.get_user_submission(TEST_GUILD_ID, "99999")
        if other_submission is None:
            print("  ✅ PASS: No submission returned for different user")
        else:
            print("  ❌ FAIL: Expected None but got submission for different user")
            return False
        
        print("\n🎉 All tests passed! The check_submission functionality works correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await session.close()


async def main():
    success = await test_check_submission()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)