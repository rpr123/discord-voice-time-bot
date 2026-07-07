# Discord Voice Time Bot

Discord voice channel activity tracker that records how long members stay in voice channels and posts weekly or monthly summaries.

## Files

- `bot.py`: Discord bot entry point.
- `voice_tracker.py`: Member time tracking, weekly/monthly summary, and JSON persistence logic.
- `.env`: Local bot settings. This file is ignored by Git.

## Environment

Create a `.env` file with these values:

```env
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=your_guild_id
LOG_CHANNEL_ID=log_channel_id
SETTLEMENT_CHANNEL_ID=settlement_channel_id
```

## Run

```powershell
python bot.py
```
