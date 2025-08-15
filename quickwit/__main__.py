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
    disabled_cogs = os.getenv('DISABLED_COGS') or ""
    disabled_cogs = disabled_cogs.split(',')
    quickwit = QuickWit(os.getenv('ADMIN_USER_ID'), disabled_cogs)
    quickwit.run(token=os.getenv('DISCORD_TOKEN'))
