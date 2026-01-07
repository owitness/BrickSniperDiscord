"""Parse Reddit posts and extract relevant information."""
import re
import html
from html.parser import HTMLParser
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from typing import Optional, Dict, Any, List, Tuple
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
    discount_percentage: Optional[int] = None


class HTMLTextExtractor(HTMLParser):
    """Extract text content, image URLs, and link URLs from HTML."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.image_urls = []
        self.link_urls = []  # URLs from <a href=""> tags
        self.in_md_div = False
        self.current_text = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            # Check if this is the markdown content div
            for attr_name, attr_value in attrs:
                if attr_name == 'class' and attr_value == 'md':
                    self.in_md_div = True
                    return
        
        # Extract image URLs from img tags
        if tag == 'img':
            for attr_name, attr_value in attrs:
                if attr_name == 'src' and attr_value:
                    self.image_urls.append(attr_value)
        
        # Extract link URLs from anchor tags
        if tag == 'a':
            for attr_name, attr_value in attrs:
                if attr_name == 'href' and attr_value:
                    # Only add if it's a real URL (not anchors, javascript, etc.)
                    if attr_value.startswith(('http://', 'https://')):
                        self.link_urls.append(attr_value)
    
    def handle_endtag(self, tag):
        if tag == 'div' and self.in_md_div:
            self.in_md_div = False
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
    
    def handle_data(self, data):
        if self.in_md_div:
            self.current_text.append(data)
        else:
            # Also collect text outside md div, but prioritize md div content
            if not self.text_parts:
                self.text_parts.append(data)
    
    def get_text(self) -> str:
        """Get extracted text, prioritizing md div content."""
        if self.text_parts:
            return ' '.join(self.text_parts)
        return ''
    
    def get_image_urls(self) -> List[str]:
        """Get all image URLs found in HTML."""
        return self.image_urls
    
    def get_link_urls(self) -> List[str]:
        """Get all link URLs found in HTML anchor tags."""
        return self.link_urls


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
    REDDIT_IMAGE_DOMAINS = {'i.redd.it', 'preview.redd.it', 'i.imgur.com', 'b.thumbs.redditmedia.com', 'a.thumbs.redditmedia.com'}
    
    @staticmethod
    def is_amazon_url(url: str) -> bool:
        """
        Check if a URL is an Amazon URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is from Amazon, False otherwise
        """
        if not url:
            return False
        
        url_lower = url.lower()
        # Check for various Amazon domains
        amazon_domains = ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de', 
                          'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.co.jp',
                          'amazon.in', 'amazon.com.au', 'amazon.com.mx', 'amazon.com.br']
        
        for domain in amazon_domains:
            if domain in url_lower:
                return True
        
        return False
    
    @staticmethod
    def convert_to_affiliate_link(url: str, affiliate_tag: str) -> str:
        """
        Convert an Amazon URL to an affiliate link.
        
        Args:
            url: Original Amazon URL
            affiliate_tag: Amazon affiliate tag (e.g., "yourtag-20")
            
        Returns:
            Amazon URL with affiliate tag added
        """
        if not url or not affiliate_tag:
            return url
        
        if not PostParser.is_amazon_url(url):
            return url
        
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Add or replace the tag parameter
            query_params['tag'] = [affiliate_tag]
            
            # Rebuild the URL
            new_query = urlencode(query_params, doseq=True)
            new_parsed = parsed._replace(query=new_query)
            affiliate_url = urlunparse(new_parsed)
            
            return affiliate_url
        except Exception:
            # If URL parsing fails, return original URL
            return url
    
    @staticmethod
    def clean_html_text(html_text: str) -> Tuple[str, List[str], List[str]]:
        """
        Clean HTML text and extract image URLs and link URLs.
        
        Args:
            html_text: HTML string to clean
            
        Returns:
            Tuple of (cleaned_text, image_urls, link_urls)
        """
        if not html_text:
            return "", [], []
        
        # Decode HTML entities
        text = html.unescape(html_text)
        
        # Extract text, images, and links using HTML parser
        extractor = HTMLTextExtractor()
        extractor.feed(text)
        
        cleaned_text = extractor.get_text()
        image_urls = extractor.get_image_urls()
        link_urls = extractor.get_link_urls()
        
        # If HTML parser didn't extract text well, fall back to regex stripping
        if not cleaned_text.strip():
            # Remove HTML comments
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            # Remove script and style tags
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Decode HTML entities again
            text = html.unescape(text)
            # Clean up whitespace
            text = ' '.join(text.split())
            cleaned_text = text
        
        # Clean up whitespace
        cleaned_text = ' '.join(cleaned_text.split())
        
        return cleaned_text, image_urls, link_urls
    
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
    def extract_discount_percentage(title: str) -> Optional[int]:
        """
        Extract discount percentage from post title.
        
        Looks for patterns like:
        - "53% off"
        - "17%"
        - "$83/17%"
        - "61.39/53% off"
        
        Args:
            title: Post title to search
            
        Returns:
            Discount percentage as integer (0-100), or None if not found
        """
        if not title:
            return None
        
        # Pattern 1: "XX% off" or "XX% Off" (case insensitive)
        match = re.search(r'(\d+)%\s*off', title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Pattern 2: "XX%" at end of title or before certain words
        match = re.search(r'(\d+)%', title)
        if match:
            # Check if it's likely a discount percentage
            # Look for context like price/discount patterns
            percent = int(match.group(1))
            # If it's between 1-100 and appears in discount context, return it
            if 1 <= percent <= 100:
                # Check if it's in a discount-like context
                # Patterns like: "$83/17%", "61.39/53%", "XX%", etc.
                context = title.lower()
                if any(keyword in context for keyword in ['off', '%', '/']):
                    return percent
        
        return None
    
    @staticmethod
    def parse_feed_entry(entry: Dict[str, Any], affiliate_tag: Optional[str] = None) -> Optional[ParsedPost]:
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
            
            # Extract discount percentage from title
            discount_percentage = PostParser.extract_discount_percentage(title)
            
            # Extract selftext (post body) - may contain HTML
            # Feedparser may put this in different fields
            raw_selftext = ""
            if "summary" in entry:
                raw_selftext = entry["summary"].strip()
            elif "content" in entry and len(entry["content"]) > 0:
                raw_selftext = entry["content"][0].get("value", "").strip()
            
            # Clean HTML and extract images and links
            selftext, html_image_urls, html_link_urls = PostParser.clean_html_text(raw_selftext)
            
            # Extract first URL - prioritize links from HTML anchor tags, then fall back to text extraction
            detected_link = None
            
            # First, check for links extracted from HTML anchor tags (most reliable)
            if html_link_urls:
                # Filter out image URLs and Reddit links (we want external links like Amazon)
                for link_url in html_link_urls:
                    # Skip if it's an image URL
                    if not PostParser.is_image_url(link_url):
                        # Skip Reddit internal links (we want external links like Amazon)
                        if 'reddit.com' not in link_url.lower():
                            detected_link = link_url
                            break
            
            # If no link found from HTML anchor tags, try extracting from raw HTML text
            if not detected_link:
                raw_urls = PostParser.URL_PATTERN.findall(raw_selftext)
                for url in raw_urls:
                    # Skip if it's an image URL
                    if not PostParser.is_image_url(url):
                        # Skip Reddit internal links
                        if 'reddit.com' not in url.lower():
                            detected_link = url
                            break
            
            # Last resort: extract from cleaned text
            if not detected_link:
                detected_link = PostParser.extract_first_url(selftext)
            
            # Convert Amazon links to affiliate links if affiliate tag is provided
            if detected_link and affiliate_tag and PostParser.is_amazon_url(detected_link):
                detected_link = PostParser.convert_to_affiliate_link(detected_link, affiliate_tag)
            
            # Extract image URL (priority order)
            image_url = None
            
            # 1. Check HTML-extracted images first (from img tags in the HTML)
            if html_image_urls:
                for img_url in html_image_urls:
                    if PostParser.is_image_url(img_url):
                        image_url = img_url
                        break
            
            # 2. Check for media_thumbnail in feed entry (Reddit RSS often includes this)
            if not image_url and "media_thumbnail" in entry and len(entry["media_thumbnail"]) > 0:
                thumbnail_url = entry["media_thumbnail"][0].get("url", "")
                if thumbnail_url and PostParser.is_image_url(thumbnail_url):
                    image_url = thumbnail_url
            
            # 3. Check for media_content (higher quality images)
            if not image_url and "media_content" in entry:
                for media in entry["media_content"]:
                    media_url = media.get("url", "")
                    if media_url and PostParser.is_image_url(media_url):
                        image_url = media_url
                        break
            
            # 4. Check if the post URL itself is an image (direct image posts)
            if not image_url and PostParser.is_image_url(link):
                image_url = link
            
            # 5. Extract image URLs from cleaned selftext as last resort
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
                image_url=image_url,
                discount_percentage=discount_percentage
            )
        except (KeyError, AttributeError, IndexError) as e:
            # Log error but don't crash
            return None
    
    @staticmethod
    def format_for_discord(post: ParsedPost, affiliate_tag: Optional[str] = None, lego_role_mention: Optional[str] = None) -> Dict[str, Any]:
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
            # Format as markdown link: [LEGO LINK](url)
            link_text = f"[LEGO LINK]({post.detected_link})"
            fields = [{
                "name": "LINK",
                "value": link_text,
                "inline": False
            }]
            embed["fields"] = fields
        
        # Build content message
        content = "🔔 New deal posted!"
        
        # Add role mention if discount is over 50% and role mention is configured
        if post.discount_percentage and post.discount_percentage > 50 and lego_role_mention:
            content = f"{lego_role_mention} {content}"
        
        payload = {
            "content": content,
            "embeds": [embed]
        }
        
        return payload

