# backend/tasks.py
import os
import concurrent.futures
from celery import Celery
import logging
from core.utils import extract_script_contents

# Import your existing classes from the core directory
from core.tiktok_profile_scraper import TikTokProfileScraper
from core.gemini_client import GeminiClient
from core.workers import process_video_worker

class NoVideosFoundError(Exception):
    """Raised when no videos are found for a given TikTok profile."""
    def __init__(self, profile_name: str, message: str = "No videos found for the profile."):
        self.profile_name = profile_name
        self.message = message
        super().__init__(f"{message} Profile: {profile_name}")


# Configure Celery
# The broker is Redis, which passes messages between Flask and the Celery worker.
# The backend is also Redis, which stores the results of your tasks.
celery = Celery(__name__, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Configure logging for this module (Celery workers will inherit this)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(processName)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

@celery.task(bind=True)
def generate_script_task(self, profile_name: str, topic: str, gemini_api_key: str, apify_api_key: str) -> dict:
    """
    The background task that runs the full scraping, transcription,
    and generation process. It also updates task state throughout.
    """
    try:
        # Step 1: Scrape TikTok profile
        self.update_state(state='SCRAPING', meta={'status': 'Scraping videos from TikTok profile...'})
        scraper = TikTokProfileScraper(api_key=apify_api_key)
        urls_to_process = scraper.scrape_profile_videos(profile_name, video_limit=5)

        if not urls_to_process:
            logger.warning(f"No videos found for profile: {profile_name}")
            raise NoVideosFoundError(profile_name)

        # Step 2: Transcribe and analyze videos
        self.update_state(state='ANALYZING', meta={'status': 'Analyzing and transcribing videos...'})
        past_scripts_data = []

        logger.info(f"Starting video processing with {os.cpu_count()} workers.")
        with concurrent.futures.ProcessPoolExecutor() as executor:
            future_to_url = {
                executor.submit(process_video_worker, url, "tiny", "output", False, "en"): url
                for url in urls_to_process
            }
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                if result.get('transcription'):
                    text = result['transcription']['text']
                    past_scripts_data.append(f"[PAST_SCRIPT]:\n{text}")

        # Step 3: Generate new script using Gemini
        self.update_state(state='GENERATING', meta={'status': 'Generating new script...'})
        final_scripts_string = "\n\n".join(past_scripts_data)
        user_input = f"{final_scripts_string}\n\n[NEW_TOPIC]:\n{topic}"

        gemini_client = GeminiClient(gemini_api_key, "core/system_prompt.txt")
        generated_script = extract_script_contents(gemini_client.generate_text(user_input))

        return {'status': 'Success', 'script': generated_script}

    except Exception as e:
        print(f"Task failed: {e}")
        raise