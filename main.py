#!/usr/bin/env python3
"""
Web Crawler for tuoitre.vn
Extracts posts, comments, images, and audio from specified categories

Usage:
    python main.py
    python main.py --categories "url1,url2,url3" --posts-per-category 35
    python main.py --format yaml
"""

import argparse
import logging
import sys
from typing import List, Tuple

import requests
from tqdm import tqdm

import config
from crawler import CategoryCrawler, PostCrawler, CommentCrawler
from utils import MediaDownloader, DataSaver
from utils.helpers import ensure_directories, respectful_delay

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class TuoitreCrawler:
    """Main crawler orchestrator"""
    
    def __init__(self, output_format: str = 'json'):
        self.session = requests.Session()
        self.category_crawler = CategoryCrawler(self.session)
        self.post_crawler = PostCrawler(self.session)
        self.comment_crawler = CommentCrawler(self.session)
        self.media_downloader = MediaDownloader(self.session)
        self.data_saver = DataSaver(output_format)
        
        # Statistics
        self.stats = {
            'total_posts': 0,
            'successful_posts': 0,
            'failed_posts': 0,
            'total_images': 0,
            'total_audio': 0,
            'total_comments': 0,
            'max_comments_post': None,
            'max_comments_count': 0
        }
    
    def crawl(self, categories: List[str], posts_per_category: int) -> None:
        """
        Main crawl method
        
        Args:
            categories: List of category URLs to crawl
            posts_per_category: Number of posts to crawl per category
        """
        ensure_directories()
        
        # Step 1: Get all post URLs from categories
        logger.info("=" * 60)
        logger.info("STEP 1: Collecting post URLs from categories")
        logger.info("=" * 60)
        
        all_posts: List[Tuple[str, str]] = []  # (url, category)
        
        for category_url in categories:
            posts = self.category_crawler.get_posts_from_category(
                category_url, 
                posts_per_category
            )
            all_posts.extend(posts)
            logger.info(f"Collected {len(posts)} posts from {category_url}")
            respectful_delay()
        
        self.stats['total_posts'] = len(all_posts)
        logger.info(f"Total posts to crawl: {self.stats['total_posts']}")
        
        # Step 2: Crawl each post
        logger.info("=" * 60)
        logger.info("STEP 2: Crawling individual posts")
        logger.info("=" * 60)
        
        for post_url, category in tqdm(all_posts, desc="Crawling posts"):
            try:
                self._process_post(post_url, category)
                self.stats['successful_posts'] += 1
            except Exception as e:
                logger.error(f"Failed to process post {post_url}: {e}")
                self.stats['failed_posts'] += 1
            
            respectful_delay()
        
        # Print summary
        self._print_summary()
    
    def _process_post(self, post_url: str, category: str) -> None:
        """Process a single post"""
        # Crawl post content
        post_data = self.post_crawler.crawl_post(post_url, category)
        if not post_data:
            raise Exception("Failed to crawl post content")
        
        post_id = post_data['postId']
        
        # Download images
        image_local_paths = []
        if post_data.get('images'):
            image_local_paths = self.media_downloader.download_images(
                post_data['images'], 
                post_id
            )
            self.stats['total_images'] += len(image_local_paths)
        
        # Download audio
        audio_local_path = None
        if post_data.get('audio'):
            audio_local_path = self.media_downloader.download_audio(
                post_data['audio'], 
                post_id
            )
            if audio_local_path:
                self.stats['total_audio'] += 1
        
        # Get comments
        comments = self.comment_crawler.get_comments(post_id, post_url)
        self.stats['total_comments'] += len(comments)
        
        # Track post with most comments
        if len(comments) > self.stats['max_comments_count']:
            self.stats['max_comments_count'] = len(comments)
            self.stats['max_comments_post'] = post_id
        
        # Prepare final data structure
        final_data = DataSaver.create_post_structure(
            post_id=post_id,
            title=post_data.get('title', ''),
            content=post_data.get('content', ''),
            author=post_data.get('author', ''),
            date=post_data.get('date', ''),
            category=category,
            url=post_url,
            audio_url=post_data.get('audio'),
            audio_local_path=audio_local_path,
            image_urls=post_data.get('images', []),
            image_local_paths=image_local_paths,
            vote_reactions=post_data.get('reactions', {}),
            comments=comments
        )
        
        # Save to file
        self.data_saver.save_post(final_data, post_id)
    
    def _print_summary(self) -> None:
        """Print crawl summary"""
        logger.info("=" * 60)
        logger.info("CRAWL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total posts attempted: {self.stats['total_posts']}")
        logger.info(f"Successful posts: {self.stats['successful_posts']}")
        logger.info(f"Failed posts: {self.stats['failed_posts']}")
        logger.info(f"Total images downloaded: {self.stats['total_images']}")
        logger.info(f"Total audio files downloaded: {self.stats['total_audio']}")
        logger.info(f"Total comments collected: {self.stats['total_comments']}")
        
        if self.stats['max_comments_post']:
            logger.info(f"Post with most comments: {self.stats['max_comments_post']} "
                       f"({self.stats['max_comments_count']} comments)")
        
        if self.stats['max_comments_count'] >= 20:
            logger.info("✓ Requirement met: At least one post has 20+ comments")
        else:
            logger.warning("⚠ Requirement NOT met: No post has 20+ comments")
        
        logger.info("=" * 60)
        logger.info(f"Data files saved to: {config.DATA_DIR}")
        logger.info(f"Images saved to: {config.IMAGES_DIR}")
        logger.info(f"Audio files saved to: {config.AUDIO_DIR}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Web crawler for tuoitre.vn',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py
    python main.py --categories "https://tuoitre.vn/thoi-su.htm,https://tuoitre.vn/the-gioi.htm,https://tuoitre.vn/phap-luat.htm"
    python main.py --posts-per-category 40 --format yaml
        """
    )
    
    parser.add_argument(
        '--categories', '-c',
        type=str,
        help='Comma-separated category URLs (default: thoi-su, the-gioi, phap-luat)'
    )
    
    parser.add_argument(
        '--posts-per-category', '-n',
        type=int,
        default=config.DEFAULT_POSTS_PER_CATEGORY,
        help=f'Number of posts per category (default: {config.DEFAULT_POSTS_PER_CATEGORY})'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['json', 'yaml'],
        default=config.OUTPUT_FORMAT,
        help=f'Output format (default: {config.OUTPUT_FORMAT})'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse categories
    if args.categories:
        categories = [url.strip() for url in args.categories.split(',')]
    else:
        categories = config.DEFAULT_CATEGORIES
    
    # Validate minimum 3 categories
    if len(categories) < 3:
        logger.error("Error: At least 3 categories are required")
        sys.exit(1)
    
    logger.info("Starting tuoitre.vn crawler")
    logger.info(f"Categories: {categories}")
    logger.info(f"Posts per category: {args.posts_per_category}")
    logger.info(f"Output format: {args.format}")
    
    # Create and run crawler
    crawler = TuoitreCrawler(output_format=args.format)
    crawler.crawl(categories, args.posts_per_category)
    
    logger.info("Crawling completed!")


if __name__ == '__main__':
    main()