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
from typing import Optional, Tuple

# Import custom classes from other modules
from tiktok_downloader import TikTokDownloader, TikTokTranscriberError
from audio_transcriber import AudioTranscriber
from tiktok_profile_scraper import TikTokProfileScraper
from secret import APIFY_API_KEY


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

def get_user_input() -> Tuple[str, bool, Optional[str]]:
    """Get TikTok URL from user input with validation."""
    downloader = TikTokDownloader()
    while True:
        url = input("Please enter a TikTok URL: ").strip()
        if url and downloader.validate_url(url):
            break
        print("Invalid or empty TikTok URL. Please try again.")
    
    keep_audio = input("Keep downloaded audio file? (y/N): ").strip().lower() == 'y'
    language = input("Language code (leave empty for auto-detection): ").strip()
    return url, keep_audio, language or None

def display_results(result: dict) -> None:
    """Display transcription results in a formatted way."""
    transcription = result['transcription']
    # video_info = result['video_info']
    
    print("\n" + "="*60)
    print("VIDEO INFORMATION")
    print("="*60)
    # print(f"Title: {video_info['title']}")
    # print(f"Uploader: {video_info['uploader']}")
    # print(f"Duration: {video_info['duration']:.1f} seconds")
    
    print("\n" + "="*60)
    print("TRANSCRIPTION RESULTS")
    print("="*60)
    print(f"Text: {transcription['text']}")
    print(f"Language: {transcription.get('language', 'Unknown')}")
    
    if 'segments' in transcription and transcription['segments']:
        print("\n" + "-"*40)
        print("DETAILED SEGMENTS:")
        print("-"*40)
        for i, seg in enumerate(transcription['segments'], 1):
            print(f"{i:2d}. [{seg['start']:6.2f}s - {seg['end']:6.2f}s] {seg['text'].strip()}")
    
    if result['audio_file']:
        print(f"\nAudio file saved: {result['audio_file']}")
    print("="*60)

def main():
    """Main function to run the TikTok transcriber."""
    parser = argparse.ArgumentParser(
        description="Transcribe audio from TikTok videos or profiles.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  - Transcribe a single video:
    python main.py --url "https://www.tiktok.com/@user/video/123"

  - Scrape and transcribe 5 videos from a profile:
    python main.py --profile-url "https://www.tiktok.com/@apifyoffice" --apify-token "YOUR_API_TOKEN" --limit 5 --keep-audio
"""
    )
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--url", help="Single TikTok video URL to process.")
    mode_group.add_argument("--profile-url", help="TikTok profile URL to scrape for recent videos.")

    parser.add_argument("--apify-token", default=APIFY_API_KEY, help="Your Apify API token (required for --profile-url).")
    parser.add_argument("--limit", type=int, default=3, help="Number of videos to process from a profile (default: 3).")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large", "large-v3"], help="Whisper model (default: small).")
    parser.add_argument("--output-dir", help="Directory to save audio files (defaults to a temporary folder).")
    parser.add_argument("--keep-audio", action="store_true", help="Keep downloaded audio file(s).")
    parser.add_argument("--language", help="Language code for transcription (e.g., 'en', 'es').")
    parser.add_argument("--filename", help="Custom filename for audio (only in single URL mode).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    
    args = parser.parse_args()

    if args.profile_url and not args.apify_token:
        parser.error("--apify-token is required when using --profile-url.")
    if args.filename and args.profile_url:
        print("Warning: --filename is ignored in profile mode.", file=sys.stderr)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Suppress loud loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        urls_to_process = []
    
        if args.url:
            urls_to_process.append(args.url)
        else:
            if not args.profile_url:
                profile_url, keep_audio, language = get_user_input()
            else:
                profile_url = args.profile_url
                keep_audio = args.keep_audio
                language = args.language

                scraper = TikTokProfileScraper(api_key=args.apify_token)
                urls_to_process = scraper.scrape_profile_videos(profile_url, args.limit)
                if not urls_to_process:
                    print("Could not find any videos to process. Exiting.")
                    sys.exit(0)

        processor = TikTokAudioProcessor(model_name=args.model)
        print(f"\nFound {len(urls_to_process)} video(s) to process.")

        for i, video_url in enumerate(urls_to_process, 1):
            print("Processing video URL: ", video_url)
            print(f"\n{'#'*25} Processing Video {i}/{len(urls_to_process)} {'#'*25}")
            result = processor.process_url(
                video_url, args.output_dir, keep_audio, language,
                filename=args.filename if not profile_url else None
            )
            display_results(result)

    except TikTokTranscriberError as e:
        logging.error(f"A processing error occurred: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}", exc_info=args.verbose)
        sys.exit(1)

if __name__ == "__main__":
    main()