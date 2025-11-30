"""
Helper functions for the web crawler
"""

import os
import re
import time
import random
import logging
import hashlib
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests
from fake_useragent import UserAgent

import config

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)


def get_random_user_agent() -> str:
    """Get a random user agent string"""
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        return random.choice(config.USER_AGENTS)


def get_headers() -> dict:
    """Get request headers with random user agent"""
    headers = config.DEFAULT_HEADERS.copy()
    headers["User-Agent"] = get_random_user_agent()
    return headers


def make_request(url: str, session: requests.Session = None, 
                 retries: int = config.MAX_RETRIES) -> Optional[requests.Response]:
    """Make an HTTP request with retry logic and error handling"""
    if session is None:
        session = requests.Session()
    
    for attempt in range(retries):
        try:
            response = session.get(
                url, 
                headers=get_headers(), 
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {url} - {e}")
            if attempt < retries - 1:
                time.sleep(config.REQUEST_DELAY * (attempt + 1))
    
    logger.error(f"All retries failed for URL: {url}")
    return None


def respectful_delay():
    """Add a respectful delay between requests"""
    delay = config.REQUEST_DELAY + random.uniform(0.5, 1.5)
    time.sleep(delay)


def extract_post_id_from_url(url: str) -> str:
    """Extract post ID from tuoitre URL"""
    match = re.search(r'-(\d+)\.htm', url)
    if match:
        return match.group(1)
    return hashlib.md5(url.encode()).hexdigest()[:12]


def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def ensure_directories():
    """Create output directories if they don't exist"""
    directories = [
        config.BASE_OUTPUT_DIR,
        config.DATA_DIR,
        config.IMAGES_DIR,
        config.AUDIO_DIR,
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Directory ensured: {directory}")


def make_absolute_url(base_url: str, relative_url: str) -> str:
    """Convert relative URL to absolute URL"""
    if relative_url.startswith(('http://', 'https://')):
        return relative_url
    return urljoin(base_url, relative_url)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename[:200]


def get_file_extension(url: str, content_type: str = None) -> str:
    """Get file extension from URL or content type"""
    parsed = urlparse(url)
    path = parsed.path
    if '.' in path:
        ext = path.rsplit('.', 1)[-1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp3', 'mp4', 'wav', 'ogg']:
            return ext
    
    if content_type:
        type_mapping = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'audio/mpeg': 'mp3',
            'audio/mp3': 'mp3',
            'audio/wav': 'wav',
            'audio/ogg': 'ogg',
        }
        return type_mapping.get(content_type.split(';')[0].strip(), 'bin')
    
    return 'bin'


def format_date(date_str: str) -> str:
    """Format date string to consistent format"""
    if not date_str:
        return ""
    return clean_text(date_str)