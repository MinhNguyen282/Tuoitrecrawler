"""
Module for crawling category pages to get post URLs
"""

import re
import logging
from typing import List, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from utils.helpers import make_request, respectful_delay, make_absolute_url

logger = logging.getLogger(__name__)


class CategoryCrawler:
    """Crawls category pages to extract post URLs"""
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
    
    def get_category_name(self, category_url: str) -> str:
        """Extract category name from URL"""
        match = re.search(r'/([^/]+)\.htm$', category_url)
        if match:
            return match.group(1)
        return "unknown"
    
    def get_posts_from_category(self, category_url: str, 
                                num_posts: int = config.DEFAULT_POSTS_PER_CATEGORY) -> List[Tuple[str, str]]:
        """
        Get post URLs from a category page
        
        Args:
            category_url: URL of the category page
            num_posts: Number of posts to retrieve
            
        Returns:
            List of tuples (post_url, category_name)
        """
        category_name = self.get_category_name(category_url)
        posts = []
        page = 1
        seen_urls = set()
        
        logger.info(f"Crawling category: {category_name} ({category_url})")
        
        while len(posts) < num_posts:
            # Construct page URL
            if page == 1:
                page_url = category_url
            else:
                base = category_url.replace('.htm', '')
                page_url = f"{base}-p{page}.htm"
            
            logger.debug(f"Fetching page: {page_url}")
            
            response = make_request(page_url, self.session)
            if not response:
                logger.warning(f"Failed to fetch page {page}, stopping")
                break
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find article links
            new_posts = self._extract_post_urls(soup, category_url, category_name, seen_urls)
            
            if not new_posts:
                logger.warning(f"No new posts found on page {page}, stopping")
                break
            
            posts.extend(new_posts)
            logger.info(f"Found {len(new_posts)} posts on page {page}, total: {len(posts)}")
            
            page += 1
            respectful_delay()
        
        return posts[:num_posts]
    
    def _extract_post_urls(self, soup: BeautifulSoup, base_url: str, 
                           category_name: str, seen_urls: set) -> List[Tuple[str, str]]:
        """Extract post URLs from a category page soup"""
        posts = []
        
        # Multiple selector strategies for tuoitre.vn
        selectors = [
            'h3.box-title-text a',
            'h2.box-title-text a',
            'a.box-category-link-title',
            '.box-focus-title a',
            'article a[href*=".htm"]',
            '.name-news a',
            '.box-category-item a.box-category-link-title',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and self._is_valid_post_url(href):
                    url = make_absolute_url(base_url, href)
                    if url not in seen_urls:
                        seen_urls.add(url)
                        posts.append((url, category_name))
        
        # Also try to find links in article/box containers
        containers = soup.select('.box-category-item, .box-focus-item, article, .news-item')
        for container in containers:
            link = container.find('a', href=True)
            if link:
                href = link.get('href')
                if href and self._is_valid_post_url(href):
                    url = make_absolute_url(base_url, href)
                    if url not in seen_urls:
                        seen_urls.add(url)
                        posts.append((url, category_name))
        
        return posts
    
    def _is_valid_post_url(self, url: str) -> bool:
        """Check if URL is a valid post URL (not category/tag page)"""
        if not url.endswith('.htm'):
            return False
        
        # Skip category pages (pagination)
        if re.search(r'-p\d+\.htm$', url):
            return False
        
        # Should have post ID pattern
        if re.search(r'-\d+\.htm$', url):
            return True
        
        return False