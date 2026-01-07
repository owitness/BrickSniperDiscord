"""Main entry point for Reddit Discord notifier."""
import logging
import signal
import sys
import threading
from typing import Optional, List
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
        self.listeners: List[RedditListener] = []
        self.threads: List[threading.Thread] = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        for listener in self.listeners:
            listener.stop()
        sys.exit(0)
    
    def _on_new_post(self, post, subreddit: str):
        """
        Callback for when a new post is detected.
        
        Args:
            post: ParsedPost object
            subreddit: Subreddit name where the post was found
        """
        logger.info(f"Processing new post from r/{subreddit}: {post.title[:50]}...")
        
        # Format for Discord
        payload = self.parser.format_for_discord(
            post, 
            affiliate_tag=self.config.AMAZON_AFFILIATE_TAG,
            lego_role_mention=self.config.LEGO_ROLE_MENTION if self.config.LEGO_ROLE_MENTION else None,
            subreddit=subreddit
        )
        
        # Send to Discord
        success = self.discord.send_post(payload)
        
        if success:
            logger.info(f"Successfully sent notification for post: {post.post_id} from r/{subreddit}")
        else:
            logger.error(f"Failed to send notification for post: {post.post_id} from r/{subreddit}")
    
    def _listener_thread(self, subreddit: str):
        """Thread function to run a listener for a specific subreddit."""
        def callback(post):
            self._on_new_post(post, subreddit)
        
        listener = RedditListener(subreddit, self.config, callback)
        self.listeners.append(listener)
        
        try:
            listener.start()
        except Exception as e:
            logger.error(f"Fatal error in listener for r/{subreddit}: {e}", exc_info=True)
    
    def run(self):
        """Run the notifier."""
        logger.info("=" * 60)
        logger.info("BrickSniper Discord - Reddit Real-Time Notifier")
        logger.info("=" * 60)
        
        subreddits = self.config.SUBREDDITS
        logger.info(f"Monitoring {len(subreddits)} subreddit(s): {', '.join(f'r/{s}' for s in subreddits)}")
        
        # Create and start a listener thread for each subreddit
        for subreddit in subreddits:
            thread = threading.Thread(
                target=self._listener_thread,
                args=(subreddit,),
                daemon=False,
                name=f"Listener-{subreddit}"
            )
            thread.start()
            self.threads.append(thread)
            logger.info(f"Started listener thread for r/{subreddit}")
        
        # Wait for all threads to complete (they run indefinitely)
        try:
            for thread in self.threads:
                thread.join()
        except KeyboardInterrupt:
            logger.info("Interrupted by user, shutting down...")
            for listener in self.listeners:
                listener.stop()
            sys.exit(0)


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

