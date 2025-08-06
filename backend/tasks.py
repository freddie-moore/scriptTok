# backend/tasks.py
import os
import concurrent.futures
from celery import Celery

# Import your existing classes from the core directory
from core.tiktok_profile_scraper import TikTokProfileScraper
from core.gemini_client import GeminiClient
from core.secret import APIFY_API_KEY, GEMINI_API_KEY
from core.workers import process_video_worker

# Configure Celery
# The broker is Redis, which passes messages between Flask and the Celery worker.
# The backend is also Redis, which stores the results of your tasks.
celery = Celery(__name__, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery.task
def generate_script_task(profile_name: str, topic: str) -> dict:
    """
    The background task that runs the full scraping, transcription,
    and generation process.
    """
    try:
        # 1. Scrape URLs (Logic from your main())
        scraper = TikTokProfileScraper(api_key=APIFY_API_KEY)
        # For a web app, you might want a fixed limit or make it an option
        urls_to_process = scraper.scrape_profile_videos(profile_name, video_limit=3)
        if not urls_to_process:
            return {'status': 'Error', 'message': 'Could not find any videos for that profile.'}

        # 2. Process videos in parallel (Logic from your main())
        past_scripts_data = []
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

        # 3. Call Gemini (Logic from your main())
        final_scripts_string = "\n\n".join(past_scripts_data)
        user_input = f"{final_scripts_string}\n\n[NEW_TOPIC]:\n{topic}"

        gemini_client = GeminiClient(GEMINI_API_KEY, "core/system_prompt.txt")
        generated_script = gemini_client.generate_text(user_input)
        
        return {'status': 'Success', 'script': generated_script}

    except Exception as e:
        # Log the full error for debugging
        print(f"Task failed: {e}")
        return {'status': 'Error', 'message': str(e)}