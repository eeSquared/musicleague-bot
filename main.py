#!/usr/bin/env python3
"""
Music League Discord Bot
A Discord bot that lets users play Music League games in Discord servers.
"""

import sys
import os

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from musicleague_bot.src import run_bot

if __name__ == "__main__":
    run_bot()
