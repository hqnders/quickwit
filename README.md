# quickwit
Quick Wit is a Discord Event organiser bot, specifically for FF14 events. Created by `hqnders` on Discord for the Ex Animo Free Company. Currently requires all intents as I have not yet looked into what is the minimum required.

To deploy (docker):
```
docker build -t quickwit:latest -f Dockerfile --network=host .
docker volume create quickwit
docker container create -e DISCORD_TOKEN=[token] -v quickwit:/app/data --name quickwit quickwit:latest
docker container start quickwit
```