"""
Module for downloading media files (images and audio)
"""

import os
import logging
from typing import Optional, List
from urllib.parse import urlparse

import requests

import config
from utils.helpers import (
    get_headers, get_file_extension, sanitize_filename,
    make_absolute_url, respectful_delay
)

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Handles downloading and saving media files"""
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
    
    def download_image(self, image_url: str, post_id: str, 
                       image_index: int = 0) -> Optional[str]:
        """Download an image and save it to the images folder"""
        try:
            post_image_dir = os.path.join(config.IMAGES_DIR, post_id)
            os.makedirs(post_image_dir, exist_ok=True)
            
            image_url = make_absolute_url(config.BASE_URL, image_url)
            
            response = self.session.get(
                image_url, 
                headers=get_headers(),
                timeout=config.REQUEST_TIMEOUT,
                stream=True
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            ext = get_file_extension(image_url, content_type)
            
            original_name = os.path.basename(urlparse(image_url).path)
            if original_name and '.' in original_name:
                filename = sanitize_filename(original_name)
            else:
                filename = f"image_{image_index + 1}.{ext}"
            
            filepath = os.path.join(post_image_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded image: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return None
    
    def download_images(self, image_urls: List[str], post_id: str) -> List[str]:
        """Download multiple images for a post"""
        downloaded = []
        for index, url in enumerate(image_urls):
            if url:
                path = self.download_image(url, post_id, index)
                if path:
                    downloaded.append(path)
                respectful_delay()
        return downloaded
    
    def download_audio(self, audio_url: str, post_id: str) -> Optional[str]:
        """Download audio file and save it to the audio folder"""
        try:
            if not audio_url:
                return None
            
            audio_url = make_absolute_url(config.BASE_URL, audio_url)
            
            response = self.session.get(
                audio_url,
                headers=get_headers(),
                timeout=config.REQUEST_TIMEOUT,
                stream=True
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            ext = get_file_extension(audio_url, content_type)
            if ext == 'bin':
                ext = 'mp3'
            
            filename = f"{post_id}.{ext}"
            filepath = os.path.join(config.AUDIO_DIR, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded audio: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to download audio {audio_url}: {e}")
            return None