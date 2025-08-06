import os
import sys
import logging
import argparse
from typing import Optional, Tuple, Dict
import concurrent.futures

# Import custom classes from other modules
from .tiktok_downloader import TikTokDownloader, TikTokTranscriberError
from .audio_transcriber import AudioTranscriber
from .tiktok_profile_scraper import TikTokProfileScraper
from .gemini_client import GeminiClient
from .secret import APIFY_API_KEY, GEMINI_API_KEY
from .tiktok_audio_processor import TikTokAudioProcessor

def process_video_worker(
    url: str, 
    model_name: str, 
    output_dir: Optional[str], 
    keep_audio: bool, 
    language: Optional[str],
    filename: Optional[str] = None
) -> Dict:
    """
    Worker function to be executed by each process.
    Initializes its own processor and handles one URL.
    """
    # Each worker process creates its own instance of the processor.
    # This correctly handles model loading and other resources per-process.
    processor = TikTokAudioProcessor(model_name=model_name)
    
    try:
        result = processor.process_url(
            url, 
            output_dir, 
            keep_audio, 
            language,
            filename=filename
        )
        # Include the original URL in the result for tracking
        result['original_url'] = url
        return result
    except Exception as e:
        # Return a dictionary with error information
        return {
            'original_url': url,
            'error': str(e),
            'transcription': None
        }
