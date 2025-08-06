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

def get_profile_name_from_user() -> str:
    """Get TikTok username from user input with validation."""
    downloader = TikTokDownloader()
    while True:
        url = input("Please enter a TikTok username to base style off of: @").strip()
        if url:
            break
        print("Invalid or empty TikTok username. Please try again.")
    
    return url

def get_topic_from_user() -> str:
    while True:
        topic = input("Please enter a topic idea: ").strip()
        if topic:
            break
        print("No topic inputted. Please try again.")
    
    return topic

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
    mode_group.add_argument("--profile-name", help="TikTok username to scrape for recent videos.")

    parser.add_argument("--topic", help="The topic idea to generate a new script around.")
    parser.add_argument("--apify-token", default=APIFY_API_KEY, help="Your Apify API token (required for --profile-url).")
    parser.add_argument("--limit", type=int, default=3, help="Number of videos to process from a profile (default: 3).")
    parser.add_argument("--model", default="tiny", choices=["tiny", "base", "small", "medium", "large", "large-v3"], help="Whisper model (default: tiny).")
    parser.add_argument("--output-dir", help="Directory to save audio files (defaults to a temporary folder).")
    parser.add_argument("--keep-audio", default="n", action="store_true", help="Keep downloaded audio file(s).")
    parser.add_argument("--language", default="en", help="Language code for transcription (e.g., 'en', 'es').")
    parser.add_argument("--filename", help="Custom filename for audio (only in single URL mode).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    
    args = parser.parse_args()

    if args.profile_name and not args.apify_token:
        parser.error("--apify-token is required when using --profile-name.")
    if args.filename and args.profile_name:
        print("Warning: --filename is ignored in profile mode.", file=sys.stderr)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Suppress loud loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)


    try:
        # urls_to_process = []
    
        # profile_name = args.profile_name if args.profile_name else get_profile_name_from_user()
        # keep_audio = args.keep_audio
        # language = args.language

        # scraper = TikTokProfileScraper(api_key=args.apify_token)
        # urls_to_process = scraper.scrape_profile_videos(profile_name, args.limit)
        # if not urls_to_process:
        #     print("Could not find any videos to process. Exiting.")
        #     sys.exit(0)

        if args.topic:
            new_topic_idea = args.topic
        else:
            new_topic_idea = get_topic_from_user()

        # print(f"\nFound {len(urls_to_process)} video(s) to process.")

        past_scripts_data = []
        urls_to_process = [
            "https://www.tiktok.com/@3blue1brown/video/7499089278320921886",
            "https://www.tiktok.com/@3blue1brown/video/7495374287524613406",
            "https://www.tiktok.com/@3blue1brown/video/7490602042063392030",
                     ]
        max_workers = os.cpu_count()
        print(f"Starting processing with up to {max_workers} parallel workers...")
        output_dir = "output"
        keep_audio = args.keep_audio
        language = args.language
        profile_name = args.profile_name
        # Use the ProcessPoolExecutor to manage parallel execution
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            
            # Submit all jobs to the executor. 
            # executor.submit schedules the function to be executed and returns a Future object.
            future_to_url = {
                executor.submit(
                    process_video_worker, 
                    url, 
                    args.model, 
                    output_dir, 
                    keep_audio, 
                    language,
                    # Pass a custom filename if needed
                    filename=None if profile_name else f"video_{i}.mp3"
                ): url 
                for i, url in enumerate(urls_to_process)
            }
            
            # Process results as they are completed
            total_videos = len(urls_to_process)
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url), 1):
                url = future_to_url[future]
                print(f"\n{'#'*25} Completed Video {i}/{total_videos} ({url}) {'#'*25}")
                
                try:
                    result = future.result() # Get the result from the worker
                    
                    if result.get('error'):
                        print(f"An error occurred while processing {url}: {result['error']}")
                        continue

                    display_results(result) # Your function to show results
                    
                    transcription_result = result['transcription']['text'] # Assuming result['transcription'] is the Whisper dict
                    formatted_script_block = f"[PAST_SCRIPT_{i}]:\n{transcription_result}"
                    past_scripts_data.append(formatted_script_block)

                except Exception as exc:
                    print(f"An exception was generated for URL {url}: {exc}")

        print("\nAll videos have been processed.")

        final_scripts_string = "\n\n".join(past_scripts_data)
        topic_string = f"[NEW_TOPIC]:\n{new_topic_idea}"

        user_input = f"{final_scripts_string}\n\n{topic_string}"

        geminiClient = GeminiClient(GEMINI_API_KEY, "system_prompt.txt")
        resp = geminiClient.generate_text(user_input)
        print(resp)

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