"""Reddit event listener using RSS feed polling."""
import logging
import time
import feedparser
import requests
from typing import Set, Callable, Optional
from config import Config
from post_parser import PostParser, ParsedPost

logger = logging.getLogger(__name__)


class RedditListener:
    """Listens for new Reddit posts via RSS feed polling."""
    
    def __init__(self, subreddit: str, config: Config, on_new_post: Callable[[ParsedPost], None]):
        """
        Initialize Reddit listener.
        
        Args:
            subreddit: Subreddit name to monitor (without r/ prefix)
            config: Application configuration
            on_new_post: Callback function called when a new post is detected
        """
        # Remove 'r/' prefix if present
        self.subreddit = subreddit[2:] if subreddit.startswith("r/") else subreddit
        self.config = config
        self.on_new_post = on_new_post
        self.seen_posts: Set[str] = set()
        self.running = False
        self.parser = PostParser()
        self.rss_url = Config.get_rss_url(self.subreddit)
    
    def _fetch_feed(self) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch the Reddit RSS feed.
        
        Returns:
            Parsed feed object, or None if fetch fails
        """
        try:
            # Reddit requires a User-Agent header
            headers = {
                'User-Agent': 'BrickSniperDiscord/1.0 (Reddit RSS Reader)'
            }
            
            response = requests.get(self.rss_url, headers=headers, timeout=10)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                try:
                    retry_seconds = int(retry_after)
                except ValueError:
                    retry_seconds = 60
                
                logger.warning(f"Rate limited by Reddit. Waiting {retry_seconds} seconds before retry...")
                time.sleep(retry_seconds)
                # Retry once after waiting
                response = requests.get(self.rss_url, headers=headers, timeout=10)
            
            response.raise_for_status()
            
            # Parse the feed content
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
            
            return feed
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error(f"Rate limited by Reddit: {e}")
            else:
                logger.error(f"Failed to fetch Reddit feed: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Reddit feed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching feed: {e}")
            return None
    
    def _process_entry(self, entry: feedparser.FeedParserDict) -> None:
        """
        Process a single feed entry.
        
        Args:
            entry: Feed entry to process
        """
        parsed_post = self.parser.parse_feed_entry(entry, affiliate_tag=self.config.AMAZON_AFFILIATE_TAG)
        
        if not parsed_post:
            logger.debug("Failed to parse feed entry, skipping")
            return
        
        # Check if we've seen this post before
        if parsed_post.post_id in self.seen_posts:
            logger.debug(f"Post {parsed_post.post_id} already seen, skipping")
            return
        
        # Mark as seen
        self.seen_posts.add(parsed_post.post_id)
        logger.info(f"New post detected: {parsed_post.title[:50]}...")
        
        # Call callback
        try:
            self.on_new_post(parsed_post)
        except Exception as e:
            logger.error(f"Error in on_new_post callback: {e}")
    
    def _poll_once(self) -> None:
        """Perform a single poll of the RSS feed."""
        feed = self._fetch_feed()
        
        if not feed:
            # Don't log warning for rate limits - already logged in _fetch_feed
            # Only log if it's a different error
            return
        
        # Process entries in reverse order (oldest first) to maintain chronological order
        # Feedparser typically returns newest first, so we reverse
        entries = list(feed.entries)
        entries.reverse()
        
        for entry in entries:
            if not self.running:
                break
            self._process_entry(entry)
    
    def start(self) -> None:
        """Start the listener (blocking)."""
        logger.info(f"Starting Reddit listener for r/{self.subreddit}")
        logger.info(f"RSS URL: {self.rss_url}")
        logger.info(f"Polling interval: {self.config.POLL_INTERVAL} seconds")
        
        self.running = True
        
        # Initial poll to populate seen_posts (don't notify on startup)
        logger.info("Performing initial poll to populate seen posts...")
        feed = self._fetch_feed()
        if feed:
            for entry in feed.entries:
                parsed_post = self.parser.parse_feed_entry(entry, affiliate_tag=self.config.AMAZON_AFFILIATE_TAG)
                if parsed_post:
                    self.seen_posts.add(parsed_post.post_id)
            logger.info(f"Initialized with {len(self.seen_posts)} seen posts")
        
        # Start polling loop
        consecutive_failures = 0
        while self.running:
            try:
                self._poll_once()
                # Reset failure counter on success
                consecutive_failures = 0
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, stopping...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Unexpected error in poll loop: {e}")
                consecutive_failures += 1
            
            if self.running:
                # Use exponential backoff if we're getting rate limited
                # Check if last fetch failed with 429
                sleep_time = self.config.POLL_INTERVAL
                if consecutive_failures > 0:
                    # Exponential backoff: 10s, 20s, 40s, max 60s
                    sleep_time = min(self.config.POLL_INTERVAL * (2 ** min(consecutive_failures, 3)), 60)
                    logger.info(f"Using backoff: sleeping {sleep_time} seconds before next poll")
                
                time.sleep(sleep_time)
    
    def stop(self) -> None:
        """Stop the listener."""
        logger.info("Stopping Reddit listener...")
        self.running = False

