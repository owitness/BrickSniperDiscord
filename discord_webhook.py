"""Discord webhook integration for sending notifications."""
import logging
import requests
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)


class DiscordWebhook:
    """Handles sending messages to Discord via webhook."""
    
    def __init__(self, webhook_url: str):
        """
        Initialize Discord webhook sender.
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "BrickSniperDiscord/1.0"
        })
    
    def send(self, payload: Dict[str, Any]) -> bool:
        """
        Send a message to Discord via webhook.
        
        Args:
            payload: Discord webhook payload dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.debug(f"Successfully sent message to Discord: {response.status_code}")
            return True
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("Retry-After", "unknown")
                logger.warning(f"Discord rate limit hit. Retry after: {retry_after} seconds")
            else:
                logger.error(f"Discord webhook HTTP error: {e} (Status: {response.status_code})")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Discord webhook request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to Discord: {e}")
            return False
    
    def send_post(self, payload: Dict[str, Any]) -> bool:
        """
        Send a post notification to Discord.
        Alias for send() for clarity.
        
        Args:
            payload: Discord webhook payload dictionary
            
        Returns:
            True if successful, False otherwise
        """
        return self.send(payload)

