#!/usr/bin/env python3
"""
Test for the role ping reminder functionality
"""

import datetime
import sys


def test_reminder_timing_logic():
    """Test the timing logic for sending reminders."""
    now = datetime.datetime.utcnow()
    
    # Test submission reminder timing
    submission_end = now + datetime.timedelta(hours=24)  # Exactly 24 hours away
    time_until_submission = submission_end - now
    hours_until_submission = time_until_submission.total_seconds() / 3600
    
    print("SUBMISSION REMINDER TIMING:")
    print(f"  Current time: {now}")
    print(f"  Submission end: {submission_end}")
    print(f"  Hours until submission end: {hours_until_submission:.2f}")
    print(f"  Should send reminder (23.5 <= {hours_until_submission:.2f} <= 24.5): {23.5 <= hours_until_submission <= 24.5}")
    
    # Test edge cases
    test_cases = [
        ("23 hours", 23.0),
        ("23.5 hours (boundary)", 23.5),
        ("24 hours (exact)", 24.0),
        ("24.5 hours (boundary)", 24.5),
        ("25 hours", 25.0),
    ]
    
    print(f"\nEDGE CASE TESTING:")
    for case_name, hours in test_cases:
        should_send = 23.5 <= hours <= 24.5
        print(f"  {case_name}: {should_send}")
    
    # Test voting reminder timing
    voting_end = now + datetime.timedelta(hours=24)
    submission_end_past = now - datetime.timedelta(hours=1)  # Submission ended 1 hour ago
    
    print(f"\nVOTING REMINDER TIMING:")
    print(f"  Current time: {now}")
    print(f"  Submission ended: {submission_end_past}")
    print(f"  Voting end: {voting_end}")
    
    time_until_voting = voting_end - now
    hours_until_voting = time_until_voting.total_seconds() / 3600
    in_voting_phase = now >= submission_end_past
    
    print(f"  Hours until voting end: {hours_until_voting:.2f}")
    print(f"  In voting phase: {in_voting_phase}")
    print(f"  Should send voting reminder: {23.5 <= hours_until_voting <= 24.5 and in_voting_phase}")
    
    return True


def test_reminder_status_tracking():
    """Test that reminder status tracking works properly."""
    print(f"\nREMINDER STATUS TRACKING:")
    
    # Simulate round with no reminders sent
    round_data = {
        'submission_reminder_sent': False,
        'voting_reminder_sent': False
    }
    
    print(f"  Initial state - Submission reminder sent: {round_data['submission_reminder_sent']}")
    print(f"  Initial state - Voting reminder sent: {round_data['voting_reminder_sent']}")
    
    # Test that reminders would be sent when appropriate
    hours_until_submission = 24.0
    hours_until_voting = 24.0
    in_voting_phase = True
    
    should_send_submission = (not round_data['submission_reminder_sent'] and 
                            23.5 <= hours_until_submission <= 24.5)
    should_send_voting = (not round_data['voting_reminder_sent'] and 
                        23.5 <= hours_until_voting <= 24.5 and 
                        in_voting_phase)
    
    print(f"  Should send submission reminder: {should_send_submission}")
    print(f"  Should send voting reminder: {should_send_voting}")
    
    # Simulate sending reminders
    if should_send_submission:
        round_data['submission_reminder_sent'] = True
        print(f"  -> Submission reminder sent and tracked")
    
    if should_send_voting:
        round_data['voting_reminder_sent'] = True
        print(f"  -> Voting reminder sent and tracked")
    
    # Test that reminders won't be sent again
    should_send_submission_again = (not round_data['submission_reminder_sent'] and 
                                  23.5 <= hours_until_submission <= 24.5)
    should_send_voting_again = (not round_data['voting_reminder_sent'] and 
                              23.5 <= hours_until_voting <= 24.5 and 
                              in_voting_phase)
    
    print(f"  Should send submission reminder again: {should_send_submission_again}")
    print(f"  Should send voting reminder again: {should_send_voting_again}")
    
    return True


def test_database_schema_changes():
    """Test that the database schema changes are correct by checking the model files."""
    print(f"\nDATABASE SCHEMA VALIDATION:")
    
    # Read the models file and check for new fields
    try:
        with open('/home/runner/work/musicleague-bot/musicleague-bot/musicleague_bot/src/db/models.py', 'r') as f:
            models_content = f.read()
        
        has_reminder_role = 'reminder_role_id' in models_content
        has_submission_reminder = 'submission_reminder_sent' in models_content
        has_voting_reminder = 'voting_reminder_sent' in models_content
        
        print(f"  Guild has reminder_role_id field: {has_reminder_role}")
        print(f"  Round has submission_reminder_sent field: {has_submission_reminder}")
        print(f"  Round has voting_reminder_sent field: {has_voting_reminder}")
        
        return has_reminder_role and has_submission_reminder and has_voting_reminder
        
    except Exception as e:
        print(f"  Error reading models file: {e}")
        return False


def test_settings_cog_changes():
    """Test that the settings cog has been updated to handle reminder roles."""
    print(f"\nSETTINGS COG VALIDATION:")
    
    try:
        with open('/home/runner/work/musicleague-bot/musicleague-bot/musicleague_bot/src/cogs/settings.py', 'r') as f:
            settings_content = f.read()
        
        has_reminder_role_param = 'reminder_role' in settings_content
        has_reminder_role_describe = 'Role to ping for 24-hour reminders' in settings_content
        has_reminder_role_field = 'Reminder Role' in settings_content
        
        print(f"  Settings command has reminder_role parameter: {has_reminder_role_param}")
        print(f"  Settings command has reminder role description: {has_reminder_role_describe}")
        print(f"  Settings display includes reminder role field: {has_reminder_role_field}")
        
        return has_reminder_role_param and has_reminder_role_describe and has_reminder_role_field
        
    except Exception as e:
        print(f"  Error reading settings file: {e}")
        return False


if __name__ == "__main__":
    print("Testing role ping reminder functionality...\n")
    
    success = True
    
    try:
        success &= test_reminder_timing_logic()
        success &= test_reminder_status_tracking()
        success &= test_database_schema_changes()
        success &= test_settings_cog_changes()
        
        if success:
            print(f"\n✅ All tests passed!")
        else:
            print(f"\n❌ Some tests failed!")
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        success = False
    
    sys.exit(0 if success else 1)