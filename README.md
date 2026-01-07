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
   - `AMAZON_AFFILIATE_TAG`: Your Amazon affiliate tag (e.g., `yourtag-20`)
     - If set, Amazon links in posts will automatically be converted to affiliate links
     - Leave empty to disable affiliate link conversion
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

## Converting to Discord Application (Multi-Server Bot)

To run this bot on multiple Discord servers, you'll need to convert it from webhooks to a Discord Application. Here's how:

### 1. Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Give it a name (e.g., "BrickSniper Bot")
4. Go to **Bot** section
5. Click **Add Bot** → **Yes, do it!**
6. Under **Token**, click **Reset Token** and copy it (you'll need this)
7. Enable **Message Content Intent** (under Privileged Gateway Intents)
8. Save changes

### 2. Invite Bot to Servers

1. Go to **OAuth2** → **URL Generator**
2. Select scopes:
   - `bot`
   - `applications.commands` (if using slash commands)
3. Select bot permissions:
   - `Send Messages`
   - `Embed Links`
   - `Read Message History`
   - `Mention Everyone` (if using role mentions)
4. Copy the generated URL
5. Open the URL in a browser and select servers to invite the bot to

### 3. Update Code for Bot Token

Replace webhook-based code with Discord.py or similar library:

```python
# Install discord.py
pip install discord.py

# Update config.py to use bot token instead of webhook
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
```

### 4. Multi-Server Configuration

You'll need a database or config file to store per-server settings:
- Channel ID for each server
- Subreddit to monitor
- Role mention settings
- Amazon affiliate tag per server

Consider using SQLite or PostgreSQL for multi-server configuration.

## Hosting on Proxmox Server

### Option 1: LXC Container (Recommended)

1. **Create LXC Container**:
   ```bash
   # In Proxmox web UI or CLI
   # Create Ubuntu 22.04 LXC container
   # Allocate: 512MB RAM, 2GB disk, 1 CPU core
   ```

2. **Access Container**:
   ```bash
   pct enter <container-id>
   ```

3. **Install Dependencies**:
   ```bash
   apt update
   apt install -y python3 python3-pip python3-venv git
   ```

4. **Clone/Upload Project**:
   ```bash
   # Option A: Clone from Git
   git clone <your-repo-url> /opt/bricksniper
   cd /opt/bricksniper
   
   # Option B: Upload via SCP
   # scp -r BrickSniperDiscord root@proxmox:/opt/bricksniper
   ```

5. **Set Up Python Environment**:
   ```bash
   cd /opt/bricksniper
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Configure Environment**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

7. **Create Systemd Service**:
   ```bash
   nano /etc/systemd/system/bricksniper.service
   ```
   
   Add this content:
   ```ini
   [Unit]
   Description=BrickSniper Discord Reddit Notifier
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/bricksniper
   Environment="PATH=/opt/bricksniper/venv/bin"
   ExecStart=/opt/bricksniper/venv/bin/python /opt/bricksniper/main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

8. **Enable and Start Service**:
   ```bash
   systemctl daemon-reload
   systemctl enable bricksniper
   systemctl start bricksniper
   systemctl status bricksniper  # Check status
   ```

9. **View Logs**:
   ```bash
   journalctl -u bricksniper -f  # Follow logs
   journalctl -u bricksniper -n 100  # Last 100 lines
   ```

### Option 2: VM (Alternative)

1. **Create VM**:
   - Ubuntu Server 22.04 LTS
   - 1GB RAM, 10GB disk minimum
   - 1 CPU core

2. **Follow LXC steps 3-9** (same setup process)

### Option 3: Docker Container

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   CMD ["python", "main.py"]
   ```

2. **Create docker-compose.yml**:
   ```yaml
   version: '3.8'
   services:
     bricksniper:
       build: .
       container_name: bricksniper
       restart: unless-stopped
       env_file:
         - .env
       volumes:
         - ./logs:/app/logs
   ```

3. **Run in Proxmox**:
   ```bash
   # Install Docker in LXC or VM
   apt install docker.io docker-compose
   
   # Run
   docker-compose up -d
   ```

### Proxmox-Specific Tips

1. **Resource Limits**:
   - Set CPU limit: 0.5-1 core
   - Set RAM limit: 256-512MB
   - Monitor usage in Proxmox dashboard

2. **Backup Strategy**:
   ```bash
   # Backup configuration
   tar -czf /backup/bricksniper-$(date +%Y%m%d).tar.gz /opt/bricksniper/.env
   
   # Add to Proxmox backup schedule
   ```

3. **Network Configuration**:
   - Ensure container/VM has internet access
   - No special firewall rules needed (outbound only)

4. **Monitoring**:
   ```bash
   # Check if service is running
   systemctl is-active bricksniper
   
   # Check resource usage
   htop  # or top
   ```

5. **Auto-Start on Boot**:
   - Systemd service handles this automatically
   - Verify: `systemctl is-enabled bricksniper`

### 24/7 Operation

Yes, the application will run 24/7 once configured with systemd. Here's how:

**Automatic Startup:**
- `WantedBy=multi-user.target` ensures the service starts automatically when the server boots
- The service starts after the network is available (`After=network.target`)

**Automatic Restart:**
- `Restart=always` means systemd will automatically restart the bot if it crashes or stops
- `RestartSec=10` waits 10 seconds before restarting (prevents restart loops)

**What This Means:**
- ✅ Runs continuously without manual intervention
- ✅ Automatically recovers from crashes
- ✅ Starts automatically after server reboots
- ✅ Survives Proxmox host restarts (if container/VM auto-starts)

**To Verify It's Running:**
```bash
systemctl status bricksniper  # Should show "active (running)"
systemctl is-enabled bricksniper  # Should show "enabled"
```

**To Stop/Start Manually (if needed):**
```bash
systemctl stop bricksniper    # Stop the service
systemctl start bricksniper   # Start the service
systemctl restart bricksniper # Restart the service
```

### Troubleshooting Proxmox Hosting

**Service Won't Start:**

1. **Check the logs** (most important):
   ```bash
   journalctl -u bricksniper -n 50 --no-pager
   ```
   This will show you the exact error message.

2. **Test manually** to see the error:
   ```bash
   cd /opt/bricksniper
   source venv/bin/activate
   python main.py
   ```

3. **Common issues and fixes**:

   - **Missing .env file**:
     ```bash
     ls -la /opt/bricksniper/.env
     # If missing, copy from example:
     cp /opt/bricksniper/.env.example /opt/bricksniper/.env
     nano /opt/bricksniper/.env  # Edit with your values
     ```

   - **Python path issues**:
     ```bash
     # Verify Python exists
     /opt/bricksniper/venv/bin/python --version
     # If error, recreate venv:
     cd /opt/bricksniper
     python3 -m venv venv --clear
     source venv/bin/activate
     pip install -r requirements.txt
     ```

   - **Missing dependencies**:
     ```bash
     cd /opt/bricksniper
     source venv/bin/activate
     pip install -r requirements.txt
     ```

   - **Permission errors**:
     ```bash
     chmod 600 /opt/bricksniper/.env
     chown root:root /opt/bricksniper/.env
     ```

   - **Invalid webhook URL in .env**:
     ```bash
     # Check your .env file
     cat /opt/bricksniper/.env
     # Make sure DISCORD_WEBHOOK_URL is complete and correct
     ```

   - **Network issues**: Test connectivity:
     ```bash
     ping 8.8.8.8
     curl https://www.reddit.com/r/legodeal/new/.rss
     ```

   - **Resource exhaustion**: Increase container/VM limits in Proxmox

4. **After fixing, restart the service**:
   ```bash
   systemctl daemon-reload
   systemctl restart bricksniper
   systemctl status bricksniper
   ```

### Security Considerations

1. **File Permissions**:
   ```bash
   chmod 600 .env  # Protect sensitive data
   chown root:root .env
   ```

2. **Firewall** (if needed):
   ```bash
   # Only allow outbound connections
   ufw default deny incoming
   ufw default allow outgoing
   ```

3. **Regular Updates**:
   ```bash
   apt update && apt upgrade -y
   source venv/bin/activate
   pip install --upgrade -r requirements.txt
   ```

## Future Enhancements

- WebSocket stream integration for even lower latency
- Multiple subreddit support
- Database for duplicate tracking across restarts
- Historical backfill
- Rate limit monitoring
- Multi-server Discord bot support
- Web dashboard for configuration

