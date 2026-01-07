"""Parse Reddit posts and extract relevant information."""
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class ParsedPost:
    """Represents a parsed Reddit post."""
    post_id: str
    title: str
    url: str
    selftext: str
    detected_link: Optional[str] = None
    image_url: Optional[str] = None


class PostParser:
    """Parser for Reddit post data."""
    
    # Regex pattern to match URLs in text
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]',
        re.IGNORECASE
    )
    
    # Image file extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
    
    # Reddit image hosting domains
    REDDIT_IMAGE_DOMAINS = {'i.redd.it', 'preview.redd.it', 'i.imgur.com'}
    
    @staticmethod
    def extract_first_url(text: str) -> Optional[str]:
        """
        Extract the first URL from text.
        
        Args:
            text: Text to search for URLs
            
        Returns:
            First URL found, or None if no URL found
        """
        if not text:
            return None
        
        match = PostParser.URL_PATTERN.search(text)
        return match.group(0) if match else None
    
    @staticmethod
    def is_image_url(url: str) -> bool:
        """
        Check if a URL points to an image.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be an image, False otherwise
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Check if it's a Reddit image domain
        for domain in PostParser.REDDIT_IMAGE_DOMAINS:
            if domain in url_lower:
                return True
        
        # Check file extension
        for ext in PostParser.IMAGE_EXTENSIONS:
            if ext in url_lower:
                return True
        
        return False
    
    @staticmethod
    def extract_image_urls(text: str) -> List[str]:
        """
        Extract all image URLs from text.
        
        Args:
            text: Text to search for image URLs
            
        Returns:
            List of image URLs found
        """
        if not text:
            return []
        
        urls = PostParser.URL_PATTERN.findall(text)
        image_urls = [url for url in urls if PostParser.is_image_url(url)]
        return image_urls
    
    @staticmethod
    def parse_feed_entry(entry: Dict[str, Any]) -> Optional[ParsedPost]:
        """
        Parse a Reddit RSS feed entry into a ParsedPost.
        
        Args:
            entry: Feed entry dictionary from feedparser
            
        Returns:
            ParsedPost object, or None if parsing fails
        """
        try:
            # Extract post ID from link (format: https://reddit.com/r/subreddit/comments/ID/title/)
            link = entry.get("link", "")
            post_id_match = re.search(r'/comments/([^/]+)/', link)
            if not post_id_match:
                return None
            
            post_id = post_id_match.group(1)
            
            # Extract title
            title = entry.get("title", "").strip()
            if not title:
                return None
            
            # Extract selftext (post body)
            # Feedparser may put this in different fields
            selftext = ""
            if "summary" in entry:
                selftext = entry["summary"].strip()
            elif "content" in entry and len(entry["content"]) > 0:
                selftext = entry["content"][0].get("value", "").strip()
            
            # Extract first URL from selftext
            detected_link = PostParser.extract_first_url(selftext)
            
            # Extract image URL
            image_url = None
            
            # Check for media_thumbnail in feed entry (Reddit RSS often includes this)
            if "media_thumbnail" in entry and len(entry["media_thumbnail"]) > 0:
                thumbnail_url = entry["media_thumbnail"][0].get("url", "")
                if thumbnail_url and PostParser.is_image_url(thumbnail_url):
                    image_url = thumbnail_url
            
            # Check for media_content (higher quality images)
            if not image_url and "media_content" in entry:
                for media in entry["media_content"]:
                    media_url = media.get("url", "")
                    if media_url and PostParser.is_image_url(media_url):
                        image_url = media_url
                        break
            
            # Check if the post URL itself is an image (direct image posts)
            if not image_url and PostParser.is_image_url(link):
                image_url = link
            
            # Extract image URLs from selftext
            if not image_url:
                image_urls = PostParser.extract_image_urls(selftext)
                if image_urls:
                    image_url = image_urls[0]  # Use first image found
            
            return ParsedPost(
                post_id=post_id,
                title=title,
                url=link,
                selftext=selftext,
                detected_link=detected_link,
                image_url=image_url
            )
        except (KeyError, AttributeError, IndexError) as e:
            # Log error but don't crash
            return None
    
    @staticmethod
    def format_for_discord(post: ParsedPost) -> Dict[str, Any]:
        """
        Format a ParsedPost for Discord webhook payload.
        
        Args:
            post: ParsedPost to format
            
        Returns:
            Discord webhook payload dictionary
        """
        embed = {
            "title": post.title,
            "url": post.url,
            "description": post.selftext[:2000] if post.selftext else "No description",  # Discord limit is 4096 for description, but we'll keep it shorter
            "color": 16711680,  # Red color
            "footer": {
                "text": f"r/legodeal"
            },
            "timestamp": None  # Will be set by Discord if available
        }
        
        # Add image if available
        if post.image_url:
            embed["image"] = {
                "url": post.image_url
            }
        
        # Add link field if detected (and it's not the same as the image)
        if post.detected_link and post.detected_link != post.image_url:
            fields = [{
                "name": "LINK",
                "value": post.detected_link,
                "inline": False
            }]
            embed["fields"] = fields
        
        payload = {
            "content": "🔔 New deal posted!",
            "embeds": [embed]
        }
        
        return payload

