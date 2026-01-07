"""Test script to fetch and send the last 5 newest posts."""
import logging
import sys
import time
import requests
import feedparser
from config import Config
from post_parser import PostParser
from discord_webhook import DiscordWebhook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_notifier(num_posts: int = 5):
    """
    Test the notifier by fetching and sending the last N newest posts.
    
    Args:
        num_posts: Number of posts to fetch and send (default: 5)
    """
    logger.info("=" * 60)
    logger.info("BrickSniper Discord - Test Mode")
    logger.info(f"Fetching and sending last {num_posts} posts")
    logger.info("=" * 60)
    
    # Initialize configuration
    try:
        config = Config()
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please ensure your .env file is set up correctly.")
        sys.exit(1)
    
    # Initialize components
    discord = DiscordWebhook(config.DISCORD_WEBHOOK_URL)
    parser = PostParser()
    
    # Process each subreddit
    subreddits = config.SUBREDDITS
    logger.info(f"Testing {len(subreddits)} subreddit(s): {', '.join(f'r/{s}' for s in subreddits)}")
    
    total_success = 0
    total_fail = 0
    
    for subreddit in subreddits:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing r/{subreddit}")
        logger.info(f"{'=' * 60}")
        
        # Fetch the RSS feed
        rss_url = Config.get_rss_url(subreddit)
        logger.info(f"Fetching feed from: {rss_url}")
        try:
            # Reddit requires a User-Agent header
            headers = {
                'User-Agent': 'BrickSniperDiscord/1.0 (Reddit RSS Reader)'
            }
            
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the feed content
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
            
            if not feed.entries:
                logger.warning(f"No entries found in r/{subreddit}. The subreddit may be empty or the feed may be unavailable.")
                continue
            
            logger.info(f"Found {len(feed.entries)} entries in feed")
            
            # Process the last N posts (feedparser returns newest first)
            posts_to_send = feed.entries[:num_posts]
            logger.info(f"Processing {len(posts_to_send)} posts from r/{subreddit}...")
            
            success_count = 0
            fail_count = 0
            
            for i, entry in enumerate(posts_to_send, 1):
                logger.info(f"\n--- Processing post {i}/{len(posts_to_send)} from r/{subreddit} ---")
                
                # Parse the post
                parsed_post = parser.parse_feed_entry(entry, affiliate_tag=config.AMAZON_AFFILIATE_TAG)
                
                if not parsed_post:
                    logger.warning(f"Failed to parse post {i}, skipping...")
                    fail_count += 1
                    continue
                
                logger.info(f"Title: {parsed_post.title[:60]}...")
                logger.info(f"Post ID: {parsed_post.post_id}")
                logger.info(f"URL: {parsed_post.url}")
                if parsed_post.detected_link:
                    logger.info(f"Detected link: {parsed_post.detected_link}")
                if parsed_post.image_url:
                    logger.info(f"Image URL: {parsed_post.image_url}")
                
                # Format for Discord
                payload = parser.format_for_discord(
                    parsed_post, 
                    affiliate_tag=config.AMAZON_AFFILIATE_TAG,
                    lego_role_mention=config.LEGO_ROLE_MENTION if config.LEGO_ROLE_MENTION else None,
                    subreddit=subreddit
                )
                
                # Send to Discord
                logger.info("Sending to Discord...")
                success = discord.send_post(payload)
                
                if success:
                    logger.info(f"✓ Successfully sent post {i} from r/{subreddit}")
                    success_count += 1
                else:
                    logger.error(f"✗ Failed to send post {i} from r/{subreddit}")
                    fail_count += 1
                
                # Small delay between posts to avoid rate limiting
                if i < len(posts_to_send):
                    time.sleep(1)
            
            total_success += success_count
            total_fail += fail_count
            
            logger.info(f"\n--- Summary for r/{subreddit} ---")
            logger.info(f"Successfully sent: {success_count}")
            logger.info(f"Failed: {fail_count}")
        
        except Exception as e:
            logger.error(f"Error processing r/{subreddit}: {e}", exc_info=True)
            continue
    
    # Overall Summary
    logger.info("\n" + "=" * 60)
    logger.info("Overall Test Summary")
    logger.info("=" * 60)
    logger.info(f"Subreddits tested: {len(subreddits)}")
    logger.info(f"Total posts successfully sent: {total_success}")
    logger.info(f"Total posts failed: {total_fail}")
    logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error during test: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point for test script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test the Reddit Discord notifier by sending the last N posts"
    )
    parser.add_argument(
        "-n", "--num-posts",
        type=int,
        default=5,
        help="Number of posts to fetch and send (default: 5)"
    )
    
    args = parser.parse_args()
    
    if args.num_posts < 1:
        logger.error("Number of posts must be at least 1")
        sys.exit(1)
    
    if args.num_posts > 25:
        logger.warning(f"Requested {args.num_posts} posts. Discord webhooks allow ~30 messages/minute.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("Test cancelled.")
            sys.exit(0)
    
    test_notifier(args.num_posts)


if __name__ == "__main__":
    main()

