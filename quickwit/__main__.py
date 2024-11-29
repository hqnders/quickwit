"""For running the bot by it's own"""
import os
import dotenv
from quickwit import quickwit

if __name__ == "__main__":
    dotenv.load_dotenv()
    quickwit.run(token=os.getenv('DISCORD_TOKEN'))
