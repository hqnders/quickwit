"""For running quickwit"""
import os
import sys
import dotenv
from quickwit import quickwit

if __name__ == "__main__":
    dotenv.load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    if token is None:
        print('$DISCORD_TOKEN not set, cannot continue')
        sys.exit(1)
    quickwit.run(token=os.getenv('DISCORD_TOKEN'))
