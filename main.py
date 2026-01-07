"""Main entry point for Reddit Discord notifier."""
import logging
import signal
import sys
from typing import Optional
from config import Config
from reddit_listener import RedditListener
from post_parser import PostParser
from discord_webhook import DiscordWebhook


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class RedditDiscordNotifier:
    """Main application class."""
    
    def __init__(self):
        """Initialize the notifier."""
        self.config = Config()
        self.config.validate()
        
        self.discord = DiscordWebhook(self.config.DISCORD_WEBHOOK_URL)
        self.parser = PostParser()
        self.listener: Optional[RedditListener] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if self.listener:
            self.listener.stop()
        sys.exit(0)
    
    def _on_new_post(self, post):
        """
        Callback for when a new post is detected.
        
        Args:
            post: ParsedPost object
        """
        logger.info(f"Processing new post: {post.title[:50]}...")
        
        # Format for Discord
        payload = self.parser.format_for_discord(
            post, 
            affiliate_tag=self.config.AMAZON_AFFILIATE_TAG,
            lego_role_mention=self.config.LEGO_ROLE_MENTION if self.config.LEGO_ROLE_MENTION else None
        )
        
        # Send to Discord
        success = self.discord.send_post(payload)
        
        if success:
            logger.info(f"Successfully sent notification for post: {post.post_id}")
        else:
            logger.error(f"Failed to send notification for post: {post.post_id}")
    
    def run(self):
        """Run the notifier."""
        logger.info("=" * 60)
        logger.info("BrickSniper Discord - Reddit Real-Time Notifier")
        logger.info("=" * 60)
        
        # Create listener
        self.listener = RedditListener(self.config, self._on_new_post)
        
        # Start listening (blocking)
        try:
            self.listener.start()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    try:
        notifier = RedditDiscordNotifier()
        notifier.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

