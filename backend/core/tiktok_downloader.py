# tiktok_downloader.py

#!/usr/bin/env python3
"""
TikTok Downloader Class

This module contains the TikTokDownloader class responsible for 
downloading audio from TikTok URLs using yt-dlp.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yt_dlp


class TikTokTranscriberError(Exception):
    """Custom exception for transcriber-related errors."""
    pass


class TikTokDownloader:
    """Class responsible for downloading audio from TikTok URLs."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the TikTok downloader.
        
        Args:
            logger: Logger instance (creates new one if None)
        """
        self.logger = logger or self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(f"{__name__}.TikTokDownloader")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the provided URL is a valid TikTok URL.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if valid TikTok URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            valid_domains = ['www.tiktok.com', 'tiktok.com', 'vm.tiktok.com', 'm.tiktok.com']
            return parsed.netloc in valid_domains
        except Exception as e:
            self.logger.debug(f"URL validation error: {e}")
            return False
    
    def get_video_info(self, url: str) -> dict:
        """
        Get video information without downloading.
        
        Args:
            url: TikTok URL
            
        Returns:
            Dictionary containing video information
            
        Raises:
            TikTokTranscriberError: If info extraction fails
        """
        if not self.validate_url(url):
            raise TikTokTranscriberError("Invalid TikTok URL provided")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                }
        except Exception as e:
            raise TikTokTranscriberError(f"Failed to get video info: {e}")
    
    def download_audio(self, url: str, output_dir: Optional[str] = None, 
                       filename: Optional[str] = None) -> str:
        """
        Download audio from TikTok URL.
        
        Args:
            url: TikTok URL to download from
            output_dir: Directory to save audio file (uses temp dir if None)
            filename: Custom filename (uses video title if None)
            
        Returns:
            Path to the downloaded audio file
            
        Raises:
            TikTokTranscriberError: If download fails
        """
        if not self.validate_url(url):
            raise TikTokTranscriberError("Invalid TikTok URL provided")
        
        # Set up output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        else:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Get video info for filename if not provided
        if filename is None:
            try:
                info = self.get_video_info(url)
                title = info['title']
                # Clean title for filename
                filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if not filename:
                    filename = "tiktok_audio"
            except Exception:
                filename = "tiktok_audio"
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, f'{filename}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            self.logger.info(f"Downloading audio from: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Find the downloaded file
                audio_file = os.path.join(output_dir, f"{filename}.wav")
                if not os.path.exists(audio_file):
                    # Fallback: find any .wav file in the directory
                    wav_files = list(Path(output_dir).glob("*.wav"))
                    if wav_files:
                        audio_file = str(wav_files[0])
                    else:
                        raise TikTokTranscriberError("Downloaded audio file not found")
                
                self.logger.info(f"Audio downloaded successfully: {audio_file}")
                return audio_file
                
        except Exception as e:
            if "yt_dlp" not in str(e):
                raise TikTokTranscriberError(f"Failed to download audio: {e}")
            raise