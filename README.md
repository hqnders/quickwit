# quickwit
Quick Wit is a Discord Event organiser bot, specifically for FF14 events. Created by `hqnders` on Discord for the Ex Animo Free Company.

To deploy (docker):
```
docker build -t quickwit:latest -f Dockerfile --network=host .
docker volume create quickwit
docker container create -e DISCORD_TOKEN=[token] -e ADMIN_USER_ID=[your-user-id] -v quickwit:/app/data --name quickwit quickwit:latest
docker container start quickwit
```

# Bot Requirements
## Emojis
The bot will automatically use '❓' in place of emojis it cannot match by name.
Currently there is an emoji associated to every value of every enumerator found in the `models/` folder.
Specificially, it tries to search for an emoji that is equal to the enumerator value, without spaces, ignoring case sensitivity.
Please also register the following emojis for full event representation:
```
Start
Duration
Organiser
People
```

## Intents
The only intent necessary is `members`, as the bot reads people's name when mentioning who joined via scheduled event interest.

# Development
## Architecture
The project attempts to follow a Model View Controller architecture whenever possible, 
with the controllers being implemented as `discord.py` cogs.

## Event Map
The following table provides an overview of which Cog interacts with which event

### Custom Events
|**Cog**            |`event_created`|`event_altered`|`registrations_altered`|`event_deleted`|
| ---               | ---           | ---           | ---                   | ---           |
|**EventCRUD**      | Dispatches    | Dispatches    | Dispatches            |               |
|**ScheduledEvents**| Listens       | Both          | Dispatches            | Listens       |
|**UI**             | Listens       | Listens       | Both                  |               |

### Built-in Events
|**Cog**            |`scheduled_event_user_add` |`scheduled_event_user_remove`  |`guild_channel_delete` |
| ---               | ---                       | ---                           | ---                   |
|**EventCRUD**      |                           |                               | Listens               |
|**ScheduledEvents**| Listens                   | Listens                       | Listens               |
