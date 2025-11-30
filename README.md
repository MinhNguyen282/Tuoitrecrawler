# Tuoitre.vn Web Crawler

Python web crawler for extracting posts, comments, images, and audio from tuoitre.vn.

Uses **Selenium WebDriver** to handle JavaScript-based pagination and dynamic content loading.

## Project Structure

```
├── main.py                           # Entry point
├── config.py                         # Configuration settings
├── requirements.txt                  # Dependencies
├── crawler/
│   ├── __init__.py
│   ├── selenium_category_crawler.py  # Selenium-based category crawler
│   ├── post_crawler.py               # Crawl individual posts
│   └── comment_crawler.py            # Crawl comments
└── utils/
    ├── __init__.py
    ├── helpers.py                    # Helper functions
    ├── media_downloader.py           # Download images/audio
    └── data_saver.py                 # Save JSON/YAML files
```

## Installation

### Prerequisites

- Python 3.8+
- Google Chrome browser (for Selenium WebDriver)

### Install Dependencies

```bash
pip install -r requirements.txt
```

The following key dependencies will be installed:
- `selenium` - Browser automation
- `webdriver-manager` - Automatic Chrome driver management
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests (for post/comment crawling)
- `lxml` - Fast XML/HTML parser

## Usage

```bash
# Default (3 categories, 35 posts each)
python main.py

# Custom categories
python main.py --categories "https://tuoitre.vn/thoi-su.htm,https://tuoitre.vn/the-gioi.htm,https://tuoitre.vn/phap-luat.htm"

# More posts, YAML format
python main.py --posts-per-category 40 --format yaml

# Verbose logging
python main.py --verbose
```

## Output

```
output/
├── data/           # JSON/YAML files per post
├── images/         # Images organized by postId
└── audio/          # Audio files named by postId
```

## JSON Structure

```json
{
  "postId": "12345678",
  "title": "Post Title",
  "content": "Article content...",
  "author": "Author Name",
  "date": "16/10/2025",
  "category": "thoi-su",
  "url": "https://tuoitre.vn/...",
  "audio": {"url": "...", "localPath": "./audio/..."},
  "images": {"urls": [...], "localPaths": [...]},
  "voteReactions": {"like": 100},
  "comments": [
    {
      "commentId": "1",
      "author": "User",
      "text": "Comment text",
      "date": "...",
      "voteReactList": {"like": 5},
      "commentReplies": [...]
    }
  ]
}
```

## Available Categories

- `https://tuoitre.vn/thoi-su.htm` - Thời sự
- `https://tuoitre.vn/the-gioi.htm` - Thế giới
- `https://tuoitre.vn/phap-luat.htm` - Pháp luật
- `https://tuoitre.vn/kinh-doanh.htm` - Kinh doanh
- `https://tuoitre.vn/cong-nghe.htm` - Công nghệ
- `https://tuoitre.vn/the-thao.htm` - Thể thao
- `https://tuoitre.vn/giai-tri.htm` - Giải trí
- `https://tuoitre.vn/giao-duc.htm` - Giáo dục

## How It Works

### JavaScript Pagination Handling

The tuoitre.vn website uses JavaScript to load additional posts dynamically. Traditional HTTP requests to pagination URLs (like `/trang-2.htm`) return cached/identical content.

This crawler uses **Selenium WebDriver** to:

1. Launch a headless Chrome browser
2. Load the category page and execute JavaScript
3. Automatically scroll and click "Load More" (Xem thêm) buttons
4. Extract post URLs from the fully rendered page
5. Continue until the required number of posts is collected

### Performance

- **Category crawling**: Uses Selenium (slower but handles dynamic content)
- **Post/comment crawling**: Uses standard HTTP requests (faster)
- Collects **35+ posts per category** (vs ~28 with static requests)

## Notes

- Respects website with 1.5-3s delays between requests
- Headless Chrome browser runs in background
- Automatic Chrome driver management (no manual setup needed)
- Retry logic for failed requests
- Graceful error handling and cleanup