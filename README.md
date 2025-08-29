# quickwit
Quick Wit is a Discord Event organiser bot, specifically for FF14 events.

To deploy (Docker):
```
docker build -t quickwit:latest -f Dockerfile --network=host .
docker volume create quickwit
docker container create -e DISCORD_TOKEN=[token] -e ADMIN_USER_ID=[your-user-id] -v quickwit:/app/data --name quickwit quickwit:latest
docker container start quickwit
```

## Environment Variables
The following environment variables are taken into account to configure running Quick Wit:
| **Variable** | **Description** |
| --- | --- |
| `DISCORD_TOKEN` | The token of the bot used to serve Quick Wit |
| `ADMIN_USER_ID` | Optional user ID of who the bot will message when encountering an error |
| `DISABLED_COGS` | Optional comma-seperated list of Cog names that will be disabled on starting up |
| `EVENT_CHANNEL_CATEGORY` | Optional case sensitive name of the event category to create event channels in |
| `EVENT_ROLE` | Optional case sensitive name of the role to ping for events |
| `ROLE_MESSAGE_IDS` | Optional comma-separated list of message IDs that users can react to to assign event roles |

# Bot Requirements
## Event Channel Category
All events shall be created under a specialized category, by default this category is named `events`.
Ensure the permissions within this category are setup correctly.
Individual event channel permissions will be edited to allow the event host to manage the channel and send messages,
while default users shall be allowed to send messages in the created thread.

## Emojis
The bot will automatically use '❓' in place of emojis it cannot match by name.
Specificially, it tries to search for every emoji without spaces and ignoring case sensitivity.
<details><summary>Please register the following emojis for full event representation</summary>

```
Start
Duration
Organiser
People
Tank
Healer
DPS
CampfireEvent
FashionShow
Judge
Speaker
Crowd
Model
FinalFantasyXIV
Event
Attending
Tentative
Late
Backup
Allrounder
Pictomancer
BlueMage
Samurai
Reaper
Ninja
Monk
Machinist
Dragoon
Dancer
Summoner
RedMage
BlackMage
Bard
WhiteMage
Scholar
Sage
Astrologian
Warrior
Paladin
GunBreaker
DarkKnight
Viper
```

</details>

## Intents
The only intents necessary are `members` and `reactions`, as the bot reads people's name when mentioning who joined via scheduled event interest.

# Development
## Architecture
The project attempts to follow a Model View Controller architecture whenever possible, 
with the controllers being implemented as `discord.py` cogs.

## Event Map
The following table provides an overview of which Cog interacts with which event

### Custom Events
|**Cog**            |`event_created`|`event_altered`|`registrations_altered`|`event_deleted`|
| ---               | ---           | ---           | ---                   | ---           |
|**EventCRUD**      | Dispatches    | Dispatches    | Dispatches            | Dispatches    |
|**ScheduledEvents**| Listens       | Both          | Dispatches            | Listens       |
|**UI**             | Listens       | Listens       | Both                  |               |

### Built-in Events
|**Cog**            |`scheduled_event_user_add` |`scheduled_event_user_remove`  |`guild_channel_delete` | `member_remove`   | `on_raw_reaction_add` | `on_raw_reaction_remove`  | `on_scheduled_event_delete`   |
| ---               | ---                       | ---                           | ---                   | ---               | ---                   | ---                       | ---                           |
|**EventCRUD**      |                           |                               | Listens               | Listens           |                       |                           |                               |
|**ScheduledEvents**| Listens                   | Listens                       | Listens               |                   |                       |                           | Listens                       |
|**Roles**          |                           |                               |                       |                   | Listens               | Listens                   |                               |
