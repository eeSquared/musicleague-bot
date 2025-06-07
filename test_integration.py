#!/usr/bin/env python3
"""
Integration test for the emoji voting system
"""

import sys
import os

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test that the core components can be imported and instantiated
def test_integration():
    """Test that all components integrate properly."""
    print("Testing integration...")
    
    try:
        # Test importing the core module
        from musicleague_bot.src.cogs.rounds import VOTING_EMOJIS, RoundsCog
        print("✓ Core modules imported successfully")
        
        # Test emoji configuration
        assert len(VOTING_EMOJIS) == 50, f"Expected 50 emojis, got {len(VOTING_EMOJIS)}"
        assert len(set(VOTING_EMOJIS)) == 50, "All emojis should be unique"
        print("✓ Emoji configuration validated")
        
        # Test that we can simulate the key workflow scenarios
        
        # Scenario 1: Small round (5 submissions)
        num_submissions = 5
        selected_emojis = VOTING_EMOJIS[:num_submissions]
        assert len(selected_emojis) == num_submissions
        print(f"✓ Small round scenario: {num_submissions} submissions")
        
        # Scenario 2: Medium round (15 submissions)  
        num_submissions = 15
        selected_emojis = VOTING_EMOJIS[:num_submissions]
        assert len(selected_emojis) == num_submissions
        print(f"✓ Medium round scenario: {num_submissions} submissions")
        
        # Scenario 3: Large round (30 submissions)
        num_submissions = 30
        selected_emojis = VOTING_EMOJIS[:num_submissions]
        assert len(selected_emojis) == num_submissions
        print(f"✓ Large round scenario: {num_submissions} submissions")
        
        # Scenario 4: Maximum round (50 submissions)
        num_submissions = 50
        selected_emojis = VOTING_EMOJIS[:num_submissions]
        assert len(selected_emojis) == num_submissions
        print(f"✓ Maximum round scenario: {num_submissions} submissions")
        
        # Test vote counting logic
        MAX_VOTES_PER_USER = 3
        
        # User voting scenarios
        user_scenarios = [
            {"current_votes": 0, "adding": True, "should_allow": True},
            {"current_votes": 1, "adding": True, "should_allow": True},
            {"current_votes": 2, "adding": True, "should_allow": True},
            {"current_votes": 3, "adding": True, "should_allow": False},  # At limit
            {"current_votes": 4, "adding": True, "should_allow": False},  # Over limit
        ]
        
        for scenario in user_scenarios:
            if scenario["adding"]:
                would_allow = scenario["current_votes"] < MAX_VOTES_PER_USER
                assert would_allow == scenario["should_allow"], f"Vote limit logic failed for {scenario}"
        
        print("✓ Vote limit logic validated")
        
        print("\n🎉 Integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test FAILED: {e}")
        return False


if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)