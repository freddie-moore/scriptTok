# audio_transcriber.py

#!/usr/bin/env python3
"""
Audio Transcriber Class

This module contains the AudioTranscriber class responsible for 
transcribing audio files using OpenAI Whisper with parallel processing support.
"""

import os
import logging
import multiprocessing as mp
from typing import Optional, List, Dict
from functools import partial

import whisper

# Import the custom exception from the downloader module
from .tiktok_downloader import TikTokTranscriberError


def transcribe_worker(args):
    """
    Worker function for parallel transcription.
    This runs in a separate process to avoid model sharing issues.
    """
    audio_path, model_name, language, device, task, transcribe_options = args
    
    try:
        # Load model in worker process
        model = whisper.load_model(model_name, device=device)
        
        # Prepare transcription options
        options = {
            'language': language,
            'task': task,
            'verbose': False,
            **transcribe_options
        }
        
        # Remove None values
        options = {k: v for k, v in options.items() if v is not None}
        
        # Transcribe
        result = model.transcribe(audio_path, **options)
        
        return {
            'audio_path': audio_path,
            'result': result,
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'audio_path': audio_path,
            'result': None,
            'status': 'error',
            'error': str(e)
        }


def process_url_worker(args):
    """
    Worker function for parallel URL processing.
    Downloads audio and prepares it for transcription.
    """
    url, output_dir, filename, downloader_class, downloader_kwargs, index = args
    
    try:
        # Create downloader instance in worker process
        downloader = downloader_class(**downloader_kwargs)
        
        # Download audio
        audio_path = downloader.download_audio(
            url, output_dir=output_dir, filename=filename
        )
        
        return {
            'index': index,
            'url': url,
            'audio_path': audio_path,
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'index': index,
            'url': url,
            'audio_path': None,
            'status': 'error',
            'error': str(e)
        }


class AudioTranscriber:
    """Class responsible for transcribing audio files using OpenAI Whisper with parallel processing."""
    
    def __init__(self, model_name: str = "tiny", device: Optional[str] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the audio transcriber.
        
        Args:
            model_name: The Whisper model to use (tiny, base, small, medium, large)
            device: Device to run model on (auto-detected if None)
            logger: Logger instance (creates new one if None)
        """
        self.model_name = model_name
        self.device = device
        self.logger = logger or self._setup_logger()
        
        # Initialize Whisper model for single file processing
        self.model = None
        self._load_model()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(f"{__name__}.AudioTranscriber")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_model(self) -> None:
        """Load the Whisper model."""
        try:
            self.logger.info(f"Loading OpenAI Whisper model: {self.model_name}")
            
            # Available models
            valid_models = ["tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3"]
            if self.model_name not in valid_models:
                raise TikTokTranscriberError(f"Invalid model name. Choose from: {valid_models}")
            
            self.model = whisper.load_model(self.model_name, device=self.device)
            self.logger.info(f"Model loaded successfully")
            
        except Exception as e:
            error_msg = f"Failed to load Whisper model: {e}"
            if "OutOfMemoryError" in str(e):
                error_msg += "\n\nTry using a smaller model: tiny, base, or small"
            raise TikTokTranscriberError(error_msg)
    
    def get_available_models(self) -> list:
        """Get list of available Whisper models."""
        return ["tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3"]
    
    def transcribe(self, audio_path: str, language: Optional[str] = None, 
                   task: str = "transcribe", **kwargs) -> dict:
        """
        Transcribe audio file using the loaded Whisper model.
        
        Args:
            audio_path: Path to the audio file
            language: Language code for transcription (auto-detect if None)
            task: Task type ("transcribe" or "translate")
            **kwargs: Additional arguments for whisper.transcribe()
            
        Returns:
            Dictionary containing transcription results
            
        Raises:
            TikTokTranscriberError: If transcription fails
        """
        if not os.path.exists(audio_path):
            raise TikTokTranscriberError(f"Audio file not found: {audio_path}")
        
        if self.model is None:
            raise TikTokTranscriberError("Model not loaded. Please initialize the transcriber first.")
        
        try:
            self.logger.info(f"Transcribing audio: {audio_path}")
            
            # Default transcription options
            transcribe_options = {
                'language': language,
                'task': task,
                'verbose': False,
                **kwargs
            }
            
            # Remove None values
            transcribe_options = {k: v for k, v in transcribe_options.items() if v is not None}
            
            # Transcribe with Whisper
            result = self.model.transcribe(audio_path, **transcribe_options)
            
            self.logger.info("Transcription completed successfully")
            return result
            
        except Exception as e:
            raise TikTokTranscriberError(f"Failed to transcribe audio: {e}")
    
    def transcribe_multiple_files(self, audio_files: List[str], language: Optional[str] = None,
                                  task: str = "transcribe", num_processes: Optional[int] = None,
                                  **kwargs) -> List[Dict]:
        """
        Transcribe multiple audio files in parallel.
        
        Args:
            audio_files: List of audio file paths
            language: Language code for transcription
            task: Task type ("transcribe" or "translate")
            num_processes: Number of parallel processes (default: CPU count)
            **kwargs: Additional arguments for transcription
            
        Returns:
            List of transcription results
        """
        if num_processes is None:
            num_processes = min(mp.cpu_count(), len(audio_files))
        
        self.logger.info(f"Starting parallel transcription of {len(audio_files)} files using {num_processes} processes")
        
        # Prepare arguments for worker processes
        args = [
            (audio_path, self.model_name, language, self.device, task, kwargs)
            for audio_path in audio_files
        ]
        
        # Process files in parallel
        with mp.Pool(processes=num_processes) as pool:
            results = pool.map(transcribe_worker, args)
        
        self.logger.info("Parallel transcription completed")
        return results
    
    def transcribe_with_timestamps(self, audio_path: str, **kwargs) -> dict:
        """
        Transcribe audio with detailed timestamp information.
        
        Args:
            audio_path: Path to the audio file
            **kwargs: Additional arguments for transcription
            
        Returns:
            Dictionary containing detailed transcription with timestamps
        """
        return self.transcribe(audio_path, word_timestamps=True, **kwargs)
