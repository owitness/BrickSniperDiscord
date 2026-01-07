# BrickSniper Discord - Reddit Real-Time Notifier

Real-time Reddit post monitoring for r/legodeal with instant Discord notifications.

## Features

- ⚡ **Ultra-low latency**: Sub-second detection and delivery
- 🔄 **Real-time monitoring**: RSS feed polling (1-2 second intervals)
- 🔗 **Link extraction**: Automatically detects and displays deal URLs
- 📊 **Stateless**: No database required
- 🛡️ **Duplicate prevention**: In-memory tracking prevents duplicate notifications

## Setup Instructions

### 1. Create Discord Webhook

1. Open your Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook**
4. Configure the webhook (name, channel, etc.)
5. Click **Copy Webhook URL**
6. Save this URL for the next step

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Discord webhook URL:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
   ```

3. Optionally customize:
   - `SUBREDDIT`: Subreddit to monitor (default: `legodeal`)
   - `POLL_INTERVAL`: Polling interval in seconds (default: `2`)

### 4. Test the Setup (Optional)

Before running the main bot, you can test your configuration by sending the last 5 newest posts:

```bash
python test_notifier.py
```

Or specify a different number of posts:

```bash
python test_notifier.py --num-posts 3
```

This will:
- Fetch the latest posts from r/legodeal
- Parse and format them
- Send them to your Discord channel
- Show a summary of successes/failures

### 5. Run

```bash
python main.py
```

The bot will start monitoring r/legodeal and send notifications to your Discord channel.

## Architecture

```
Reddit RSS Feed → Event Listener → Parser/Filter → Discord Webhook
```

- **Event Listener**: Polls Reddit RSS feed every 1-2 seconds
- **Parser**: Extracts post title, URL, body text, and first outbound link
- **Discord Webhook**: Sends formatted embed messages instantly

## Message Format

Each notification includes:
- **Title**: Clickable link to the Reddit post
- **Description**: Post body text
- **Image**: Automatically detected images from the post (if any)
- **Link Field**: First detected URL from the post (if any, and different from image)

## Troubleshooting

- **No notifications**: Check that your webhook URL is correct and the bot has permission to post in the channel
- **Rate limiting**: Discord webhooks allow ~30 messages/minute. r/legodeal volume is typically low enough to stay within limits
- **Duplicate messages**: The bot tracks seen posts in memory. Restarting will reset this (duplicates may appear after restart)

## Future Enhancements

- WebSocket stream integration for even lower latency
- Multiple subreddit support
- Database for duplicate tracking across restarts
- Historical backfill
- Rate limit monitoring

