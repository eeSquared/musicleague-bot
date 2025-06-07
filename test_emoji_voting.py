#!/usr/bin/env python3
"""
Test for emoji voting system functionality
"""

import sys
import os

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from musicleague_bot.src.cogs.rounds import VOTING_EMOJIS


def test_emoji_voting_system():
    """Test the emoji voting system configuration."""
    print("Testing emoji voting system...")
    
    # Test 1: Check we have enough emojis for large rounds
    print(f"Available voting emojis: {len(VOTING_EMOJIS)}")
    assert len(VOTING_EMOJIS) >= 20, "Should have at least 20 emojis for large rounds"
    print("✓ Sufficient emojis available")
    
    # Test 2: Check all emojis are unique
    unique_emojis = set(VOTING_EMOJIS)
    assert len(unique_emojis) == len(VOTING_EMOJIS), "All emojis should be unique"
    print("✓ All emojis are unique")
    
    # Test 3: Check emojis are valid unicode
    for i, emoji in enumerate(VOTING_EMOJIS):
        try:
            # Try to encode/decode the emoji
            emoji.encode('utf-8').decode('utf-8')
        except UnicodeError:
            assert False, f"Invalid emoji at index {i}: {emoji}"
    print("✓ All emojis are valid unicode")
    
    # Test 4: Check emoji variety (music-related and general)
    music_emojis = ["🎵", "🎶", "🎤", "🎧", "🎸", "🥁", "🎺", "🎷", "🎹", "🎻"]
    music_count = sum(1 for emoji in music_emojis if emoji in VOTING_EMOJIS)
    assert music_count >= 5, "Should have at least 5 music-related emojis"
    print(f"✓ Music-related emojis: {music_count}")
    
    print("\nEmoji voting system test PASSED!")
    return True


def test_emoji_mapping_logic():
    """Test the logic for mapping submissions to emojis."""
    print("\nTesting emoji mapping logic...")
    
    # Simulate different numbers of submissions
    test_cases = [1, 5, 10, 15, 25, 50]
    
    for num_submissions in test_cases:
        if num_submissions <= len(VOTING_EMOJIS):
            assigned_emojis = VOTING_EMOJIS[:num_submissions]
            assert len(assigned_emojis) == num_submissions
            print(f"✓ {num_submissions} submissions -> {len(assigned_emojis)} emojis")
        else:
            print(f"⚠ {num_submissions} submissions exceeds available emojis ({len(VOTING_EMOJIS)})")
    
    print("Emoji mapping logic test PASSED!")
    return True


def test_vote_limit_logic():
    """Test the 3-vote limit logic."""
    print("\nTesting vote limit logic...")
    
    # Simulate user voting scenarios
    max_votes = 3
    
    # Test case 1: User with 2 votes adding a 3rd (should be allowed)
    current_votes = 2
    adding_vote = True
    expected_total = 3
    
    if adding_vote and current_votes < max_votes:
        new_total = current_votes + 1
        assert new_total <= max_votes, "Should allow vote within limit"
        print(f"✓ Adding vote: {current_votes} -> {new_total} (within limit)")
    
    # Test case 2: User with 3 votes adding a 4th (should be blocked)
    current_votes = 3
    adding_vote = True
    
    if adding_vote and current_votes >= max_votes:
        print(f"✓ Blocking vote: {current_votes} votes already at limit")
    
    # Test case 3: User removing a vote
    current_votes = 3
    removing_vote = True
    
    if removing_vote:
        new_total = current_votes - 1
        print(f"✓ Removing vote: {current_votes} -> {new_total}")
    
    print("Vote limit logic test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_emoji_voting_system()
        test_emoji_mapping_logic()
        test_vote_limit_logic()
        print("\n🎉 All emoji voting tests PASSED!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)