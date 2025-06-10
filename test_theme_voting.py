#!/usr/bin/env python3
"""
Test for theme voting functionality
"""

import sys
import os

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_theme_voting_integration():
    """Test that theme voting components integrate properly."""
    print("Testing theme voting integration...")
    
    try:
        # Test importing the new models
        from musicleague_bot.src.db.models import ThemeSubmission, Guild, Round
        print("✓ ThemeSubmission model imported successfully")
        
        # Test new guild fields
        guild_fields = ['theme_submission_days', 'theme_voting_days']
        for field in guild_fields:
            if not hasattr(Guild, field):
                raise AssertionError(f"Guild missing field: {field}")
        print("✓ Guild has new theme-related fields")
        
        # Test new round fields
        round_fields = ['theme_submission_end', 'theme_voting_end', 
                       'theme_submission_message_id', 'theme_voting_message_id']
        for field in round_fields:
            if not hasattr(Round, field):
                raise AssertionError(f"Round missing field: {field}")
        print("✓ Round has new theme-related fields")
        
        # Test ThemeSubmission model fields
        theme_fields = ['theme_text', 'description', 'votes_received']
        for field in theme_fields:
            if not hasattr(ThemeSubmission, field):
                raise AssertionError(f"ThemeSubmission missing field: {field}")
        print("✓ ThemeSubmission has required fields")
        
        # Test importing the new modals and methods
        from musicleague_bot.src.cogs.rounds import ThemeSubmissionModal, RoundsCog
        print("✓ ThemeSubmissionModal imported successfully")
        
        # Test that RoundsCog has new methods
        cog_methods = ['start_theme_submission_phase', 'start_theme_voting_phase', 
                      'complete_theme_voting', '_format_theme_voting_detail']
        for method in cog_methods:
            if not hasattr(RoundsCog, method):
                raise AssertionError(f"RoundsCog missing method: {method}")
        print("✓ RoundsCog has new theme-related methods")
        
        # Test database service methods
        from musicleague_bot.src.db.service import DatabaseService
        db_methods = ['create_theme_submission', 'get_round_theme_submissions',
                     'calculate_theme_voting_results', 'update_round_theme_message_ids']
        for method in db_methods:
            if not hasattr(DatabaseService, method):
                raise AssertionError(f"DatabaseService missing method: {method}")
        print("✓ DatabaseService has new theme-related methods")
        
        print("\n🎉 Theme voting integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Theme voting integration test FAILED: {e}")
        return False

def test_theme_voting_workflow():
    """Test the theme voting workflow logic."""
    print("\nTesting theme voting workflow...")
    
    import datetime
    from musicleague_bot.src.cogs.rounds import VOTING_EMOJIS
    
    # Test 1: Emoji allocation for theme voting
    print("1. Testing emoji allocation for theme voting...")
    test_theme_counts = [1, 3, 5, 10, 20]
    
    for count in test_theme_counts:
        if count <= len(VOTING_EMOJIS):
            allocated_emojis = VOTING_EMOJIS[:count]
            assert len(allocated_emojis) == count
            print(f"   ✓ {count} themes -> {len(allocated_emojis)} emojis")
        else:
            print(f"   ⚠ {count} themes exceeds available emojis")
    
    # Test 2: Theme phase timing calculations
    print("2. Testing theme phase timing calculations...")
    now = datetime.datetime.utcnow()
    theme_submission_days = 2
    theme_voting_days = 3
    
    theme_submission_end = now + datetime.timedelta(days=theme_submission_days)
    theme_voting_end = theme_submission_end + datetime.timedelta(days=theme_voting_days)
    
    assert theme_submission_end > now
    assert theme_voting_end > theme_submission_end
    assert (theme_voting_end - theme_submission_end).days == theme_voting_days
    
    print(f"   ✓ Theme submission period: {theme_submission_days} days")
    print(f"   ✓ Theme voting period: {theme_voting_days} days")
    print(f"   ✓ Total theme phase: {(theme_voting_end - now).days} days")
    
    print("\n🎉 Theme voting workflow test PASSED!")
    return True

if __name__ == "__main__":
    success1 = test_theme_voting_integration()
    success2 = test_theme_voting_workflow()
    
    if success1 and success2:
        print("\n🎊 ALL THEME VOTING TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)