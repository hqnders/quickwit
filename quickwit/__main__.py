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
    admin_user_id = os.getenv('ADMIN_USER_ID')
    if admin_user_id is None:
        print('$ADMIN_USER_ID not set, cannot continue')
        sys.exit(1)
    quickwit = QuickWit(int(admin_user_id), disabled_cogs)
    quickwit.run(token=token)
