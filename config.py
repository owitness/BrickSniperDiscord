"""Configuration management for Reddit Discord notifier."""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # Discord webhook URL (required)
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    
    # Subreddits to monitor (comma-separated, default: legodeal,legodeals)
    # Example: "legodeal,legodeals" or "legodeal"
    SUBREDDITS_STR = os.getenv("SUBREDDIT", os.getenv("SUBREDDITS", "legodeal,legodeals"))
    
    @property
    def SUBREDDITS(self) -> List[str]:
        """Get list of subreddits to monitor."""
        # Split by comma, strip whitespace, filter empty strings
        subreddits = [s.strip() for s in self.SUBREDDITS_STR.split(",") if s.strip()]
        # Remove 'r/' prefix if present
        subreddits = [s[2:] if s.startswith("r/") else s for s in subreddits]
        return subreddits if subreddits else ["legodeal"]
    
    # Backward compatibility: first subreddit
    @property
    def SUBREDDIT(self) -> str:
        """Get first subreddit (for backward compatibility)."""
        return self.SUBREDDITS[0]
    
    # Amazon affiliate tag (optional) - e.g., "yourtag-20"
    # If set, Amazon links will be converted to affiliate links
    AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "")
    
    # Discord role to mention for deals over 50% off (optional)
    # Format: <@&ROLE_ID> or @LEGO (if role name is "LEGO")
    # Leave empty to disable role mentions
    LEGO_ROLE_MENTION = os.getenv("LEGO_ROLE_MENTION", "<@&ROLE_ID>")
    
    # Polling interval in seconds (default: 10)
    # Reddit rate limits aggressive polling. 10 seconds is safer.
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))
    
    # Reddit RSS feed URL (for backward compatibility)
    @property
    def REDDIT_RSS_URL(self) -> str:
        """Generate Reddit RSS feed URL for the first configured subreddit."""
        return f"https://www.reddit.com/r/{self.SUBREDDIT}/new/.rss"
    
    @staticmethod
    def get_rss_url(subreddit: str) -> str:
        """Generate Reddit RSS feed URL for a specific subreddit."""
        # Remove 'r/' prefix if present
        subreddit_clean = subreddit[2:] if subreddit.startswith("r/") else subreddit
        return f"https://www.reddit.com/r/{subreddit_clean}/new/.rss"
    
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

