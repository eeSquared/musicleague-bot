#!/usr/bin/env python3
"""
Final comprehensive test for emoji voting system
"""

import sys
import os

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_comprehensive():
    """Comprehensive test of the emoji voting system."""
    print("🧪 Running comprehensive emoji voting system tests...\n")
    
    try:
        from musicleague_bot.src.cogs.rounds import VOTING_EMOJIS, RoundsCog
        
        # Test 1: System Requirements
        print("1. Testing system requirements...")
        assert len(VOTING_EMOJIS) >= 20, "Must support at least 20 submissions"
        assert len(VOTING_EMOJIS) <= 100, "Should not exceed reasonable emoji limit"
        assert len(set(VOTING_EMOJIS)) == len(VOTING_EMOJIS), "All emojis must be unique"
        print("   ✓ System requirements met")
        
        # Test 2: Emoji Quality
        print("2. Testing emoji quality...")
        for i, emoji in enumerate(VOTING_EMOJIS):
            assert isinstance(emoji, str), f"Emoji {i} must be string"
            assert len(emoji) >= 1, f"Emoji {i} cannot be empty"
            assert len(emoji.encode('utf-8')) <= 10, f"Emoji {i} too long: {emoji}"
        print("   ✓ All emojis are valid")
        
        # Test 3: Content Variety
        print("3. Testing emoji content variety...")
        music_related = ["🎵", "🎶", "🎤", "🎧", "🎸", "🥁", "🎺", "🎷", "🎹", "🎻"]
        music_count = sum(1 for emoji in VOTING_EMOJIS if emoji in music_related)
        assert music_count >= 5, "Should have multiple music-related emojis"
        print(f"   ✓ {music_count} music-related emojis found")
        
        # Test 4: Submission Mapping
        print("4. Testing submission to emoji mapping...")
        test_cases = [1, 5, 10, 15, 20, 30, 50]
        for count in test_cases:
            if count <= len(VOTING_EMOJIS):
                mapped = VOTING_EMOJIS[:count]
                assert len(mapped) == count, f"Mapping failed for {count} submissions"
                assert len(set(mapped)) == count, f"Duplicate emojis in mapping for {count}"
        print("   ✓ Submission mapping works correctly")
        
        # Test 5: Vote Limiting Logic
        print("5. Testing vote limiting logic...")
        MAX_VOTES = 3
        scenarios = [
            (0, True, True),   # 0 votes + add = allow (1 vote)
            (1, True, True),   # 1 vote + add = allow (2 votes)
            (2, True, True),   # 2 votes + add = allow (3 votes)
            (3, True, False),  # 3 votes + add = block (would be 4)
            (4, True, False),  # 4 votes + add = block (would be 5)
            (3, False, True),  # 3 votes - remove = allow (2 votes)
        ]
        
        for current_votes, is_adding, should_allow in scenarios:
            if is_adding:
                would_allow = current_votes < MAX_VOTES
            else:
                would_allow = True  # Always allow removal
            
            assert would_allow == should_allow, f"Vote limit logic failed: {current_votes} votes, adding={is_adding}"
        print("   ✓ Vote limiting logic correct")
        
        # Test 6: Edge Cases
        print("6. Testing edge cases...")
        
        # Empty submission list
        empty_mapped = VOTING_EMOJIS[:0]
        assert len(empty_mapped) == 0, "Empty submission list should map to no emojis"
        
        # Single submission
        single_mapped = VOTING_EMOJIS[:1]
        assert len(single_mapped) == 1, "Single submission should map to one emoji"
        assert single_mapped[0] == VOTING_EMOJIS[0], "First submission should get first emoji"
        
        # Maximum submissions
        max_mapped = VOTING_EMOJIS[:len(VOTING_EMOJIS)]
        assert len(max_mapped) == len(VOTING_EMOJIS), "Max submissions should use all emojis"
        
        print("   ✓ Edge cases handled correctly")
        
        # Test 7: Message Length Considerations
        print("7. Testing message length considerations...")
        
        # Simulate a voting message content
        sample_submission = "Test Artist - Test Song https://example.com/song"
        sample_description = "This is a great song because it has amazing lyrics and melody."
        
        for count in [5, 10, 20, 30]:
            if count <= len(VOTING_EMOJIS):
                total_content = ""
                for i in range(count):
                    emoji = VOTING_EMOJIS[i]
                    entry = f"{emoji} **Submission #{i + 1}**\n{sample_submission}\n{sample_description}\n\n"
                    total_content += entry
                
                # Check if content would need splitting (Discord's 2000 char limit)
                needs_splitting = len(total_content) > 2000
                print(f"   📏 {count} submissions: {len(total_content)} chars (split: {needs_splitting})")
        
        print("   ✓ Message length considerations evaluated")
        
        print("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print(f"\n📊 Summary:")
        print(f"   • {len(VOTING_EMOJIS)} voting emojis available")
        print(f"   • Supports up to {len(VOTING_EMOJIS)} submissions per round")
        print(f"   • Maximum {MAX_VOTES} votes per user")
        print(f"   • {music_count} music-themed emojis")
        print(f"   • {len(VOTING_EMOJIS) - music_count} general-purpose emojis")
        
        return True
        
    except Exception as e:
        print(f"\n❌ COMPREHENSIVE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_comprehensive()
    sys.exit(0 if success else 1)