# main.py

#!/usr/bin/env python3
"""
TikTok Audio Transcriber - Main Application

This script orchestrates the process of downloading audio from a TikTok URL
or an entire profile, and transcribing it using OpenAI Whisper.
"""

import os
import sys
import logging
import argparse
from typing import Optional, Tuple, Dict
import concurrent.futures

# Import custom classes from other modules
from core.tiktok_downloader import TikTokDownloader, TikTokTranscriberError
from core.audio_transcriber import AudioTranscriber
from core.tiktok_profile_scraper import TikTokProfileScraper
from core.gemini_client import GeminiClient
from core.secret import APIFY_API_KEY, GEMINI_API_KEY

class TikTokAudioProcessor:
    """Main orchestrator class that combines downloading and transcription."""
    
    def __init__(self, model_name: str = "small", device: Optional[str] = None):
        """
        Initialize the TikTok audio processor.
        
        Args:
            model_name: Whisper model to use for transcription
            device: Device to run model on (auto-detected if None)
        """
        self.logger = self._setup_logger()
        self.downloader = TikTokDownloader(logger=self.logger)
        self.transcriber = AudioTranscriber(model_name, device, logger=self.logger)
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def process_url(self, url: str, output_dir: Optional[str] = None, 
                    keep_audio: bool = False, language: Optional[str] = None,
                    filename: Optional[str] = None) -> dict:
        """
        Complete pipeline: download audio from TikTok URL and transcribe.
        
        Args:
            url: TikTok URL to process
            output_dir: Directory for audio files
            keep_audio: Whether to keep the downloaded audio file
            language: Language code for transcription
            filename: Custom filename for audio file
            
        Returns:
            Dictionary containing transcription results and metadata
        """
        audio_path = None
        try:
            audio_path = self.downloader.download_audio(
                url, output_dir=output_dir, filename=filename
            )
            transcription_result = self.transcriber.transcribe(audio_path, language=language)
            
            return {
                'transcription': transcription_result,
                'audio_file': audio_path if keep_audio else None,
            }
        finally:
            if audio_path and not keep_audio and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    self.logger.info(f"Cleaned up audio file: {audio_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up audio file: {e}")