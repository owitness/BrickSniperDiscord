"""Configuration management for Reddit Discord notifier."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # Discord webhook URL (required)
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    
    # Subreddit to monitor (default: legodeal)
    SUBREDDIT = os.getenv("SUBREDDIT", "legodeal")
    
    # Amazon affiliate tag (optional) - e.g., "yourtag-20"
    # If set, Amazon links will be converted to affiliate links
    AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "")
    
    # Discord role to mention for deals over 50% off (optional)
    # Format: <@&ROLE_ID> or @LEGO (if role name is "LEGO")
    # Leave empty to disable role mentions
    LEGO_ROLE_MENTION = os.getenv("LEGO_ROLE_MENTION", "<@&ROLE_ID>")
    
    # Polling interval in seconds (default: 2)
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))
    
    # Reddit RSS feed URL
    @property
    def REDDIT_RSS_URL(self) -> str:
        """Generate Reddit RSS feed URL for the configured subreddit."""
        return f"https://www.reddit.com/r/{self.SUBREDDIT}/new/.rss"
    
    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.DISCORD_WEBHOOK_URL:
            raise ValueError(
                "DISCORD_WEBHOOK_URL is required. "
                "Please set it in your .env file or environment variables."
            )
        
        if not self.DISCORD_WEBHOOK_URL.startswith("https://discord.com/api/webhooks/"):
            raise ValueError(
                "DISCORD_WEBHOOK_URL appears to be invalid. "
                "It should start with 'https://discord.com/api/webhooks/'"
            )
        
        if self.POLL_INTERVAL < 1:
            raise ValueError("POLL_INTERVAL must be at least 1 second")

