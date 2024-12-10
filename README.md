# quickwit
Quick Wit is a Discord Event organiser bot, specifically for FF14 events. Created by `hqnders` on Discord for the Ex Animo Free Company. Currently requires all intents as I have not yet looked into what is the minimum required.

To deploy (docker):
```
docker build -t quickwit:latest -f Dockerfile --network=host .
docker volume create quickwit
docker container create -e DISCORD_TOKEN=[token] -v quickwit:/app/data --name quickwit quickwit:latest
docker container start quickwit
```

# Requirements
## Emoji's
The bot will automatically use '❓' in place of emojis it cannot match by name.
Please register emojis with the following names for full support:
```
Attendance Statusses:
Attending, Bench, Tentative, Late

Event Overview:
Start, Duration, Organiser, People

Event Types:
Event, FinalFantasyXIV, FashionShow, CampfireEvent

Jobs:
Jobless, Allrounder
Warrior, Paladin, DarkKnight, Gunbreaker
WhiteMage, Scholar, Astrologian, Sage
Monk, Dragoon, Ninja, Samurai, Viper, Reaper
Bard, Machinist, Dancer
BlackMage, Summoner, RedMage, Pictomancer, BlueMage
Crowd, Model, Judge, Speaker
```

## Intents
The only intent necessary is `members`, as the bot reads people's name when mentioning who joined via scheduled event interest.