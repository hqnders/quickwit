"""For running quickwit"""
import os
import sys
import dotenv
from quickwit import QuickWit

if __name__ == "__main__":
    dotenv.load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    if token is None:
        print('$DISCORD_TOKEN not set, cannot continue')
        sys.exit(1)
    quickwit = QuickWit(os.getenv('ADMIN_USER_ID'))
    quickwit.run(token=os.getenv('DISCORD_TOKEN'))
