"""
Configuration settings for tuoitre.vn web crawler
"""

import os

# Base URLs
BASE_URL = "https://tuoitre.vn"

# Default categories to crawl (can be overridden via command line)
DEFAULT_CATEGORIES = [
    "https://tuoitre.vn/thoi-su.htm",
    "https://tuoitre.vn/the-gioi.htm", 
    "https://tuoitre.vn/phap-luat.htm"
]

# Crawling settings
DEFAULT_POSTS_PER_CATEGORY = 35  # To get 100+ total across 3 categories
REQUEST_DELAY = 1.5  # Seconds between requests (be respectful)
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Output directories
BASE_OUTPUT_DIR = "output"
DATA_DIR = os.path.join(BASE_OUTPUT_DIR, "data")
IMAGES_DIR = os.path.join(BASE_OUTPUT_DIR, "images")
AUDIO_DIR = os.path.join(BASE_OUTPUT_DIR, "audio")

# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Request headers
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Comments API endpoint (tuoitre uses an API for comments)
COMMENTS_API_URL = "https://id.tuoitre.vn/api/getlist-comment.api"

# Data output format: 'json' or 'yaml'
OUTPUT_FORMAT = "json"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"