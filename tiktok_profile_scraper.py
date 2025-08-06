# profile_scraper.py

#!/usr/bin/env python3
"""
TikTok Profile Scraper Class

This module contains the TikTokProfileScraper class, which uses the Apify API
to scrape video URLs from a given TikTok profile.
"""

import logging
from typing import Optional, List
from urllib.parse import urlparse

from apify_client import ApifyClient
from tiktok_downloader import TikTokTranscriberError

class TikTokProfileScraper:
    """Uses Apify to scrape video URLs from a TikTok profile."""

    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the TikTok profile scraper.

        Args:
            api_key: Your Apify API token.
            logger: Logger instance (creates new one if None).
        
        Raises:
            TikTokTranscriberError: If the API key is not provided.
        """
        if not api_key:
            raise TikTokTranscriberError("An Apify API key is required for profile scraping.")
            
        self.logger = logger or self._setup_logger()
        try:
            self.client = ApifyClient(api_key)
        except Exception as e:
            raise TikTokTranscriberError(f"Failed to initialize Apify client: {e}")

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(f"{__name__}.TikTokProfileScraper")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def _extract_username(self, profile_url: str) -> str:
        """
        Extracts the username from a TikTok profile URL.

        Args:
            profile_url: The full URL of the TikTok profile.

        Returns:
            The extracted username.
        
        Raises:
            TikTokTranscriberError: If the username cannot be extracted.
        """
        try:
            # Valid URLs: https://www.tiktok.com/@username
            path_segments = urlparse(profile_url).path.strip('/').split('/')
            if path_segments and path_segments[0].startswith('@'):
                return path_segments[0][1:]
            raise ValueError("Path does not contain a valid @username format.")
        except Exception as e:
            self.logger.error(f"Could not extract username from URL '{profile_url}': {e}")
            raise TikTokTranscriberError(f"Invalid TikTok profile URL format: {profile_url}")

    def scrape_profile_videos(self, username: str, video_limit: int = 2) -> List[str]:
        """
        Runs the Apify TikTok Profile Scraper Actor to get video URLs.

        Args:
            profile_url: The URL of the TikTok profile to scrape.
            video_limit: The maximum number of video URLs to retrieve.

        Returns:
            A list of video URLs.
            
        Raises:
            TikTokTranscriberError: If the scraping process fails.
        """
        self.logger.info(f"Starting scrape for TikTok profile: {username} (limit: {video_limit})")

        run_input = {
            "profiles": [username],
            "resultsPerPage": video_limit,
            "shouldDownloadVideos": False,  # We only need the URLs, saving time and resources
        }
        
        try:
            # Run the Actor and wait for it to finish
            self.logger.info("Calling Apify Actor 'clockworks/tiktok-profile-scraper'...")
            actor_run = self.client.actor("clockworks/tiktok-profile-scraper").call(run_input=run_input)
            
            self.logger.info(f"Apify Actor run finished. Dataset ID: {actor_run['defaultDatasetId']}")
            
            video_urls = []
            dataset = self.client.dataset(actor_run['defaultDatasetId'])

            # Extract video URLs
            for video_data in dataset.iterate_items():
                if 'webVideoUrl' in video_data and video_data["webVideoUrl"]:
                    video_urls.append(video_data["webVideoUrl"])
              
            if not video_urls:
                 self.logger.warning(f"No video URLs found for profile '{username}'. The profile might be private or have no videos.")

            self.logger.info(f"Successfully scraped {len(video_urls)} video URLs.")

            return video_urls

        except Exception as e:
            self.logger.error(f"Apify Actor call failed: {e}")
            raise TikTokTranscriberError(f"Failed to scrape profile '{username}'. See logs for details.")