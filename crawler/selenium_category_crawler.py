"""
Module for crawling category pages using Selenium to handle JavaScript pagination
"""

import re
import time
import logging
from typing import List, Tuple
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

import config
from utils.helpers import make_absolute_url

logger = logging.getLogger(__name__)


class SeleniumCategoryCrawler:
    """Crawls category pages using Selenium to handle JavaScript-based pagination"""

    def __init__(self, headless: bool = True):
        """
        Initialize Selenium crawler

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        if self.driver:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Remove webdriver property
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        logger.info("Selenium WebDriver initialized")

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Selenium WebDriver closed")

    def get_category_name(self, category_url: str) -> str:
        """Extract category name from URL"""
        match = re.search(r'/([^/]+)\.htm$', category_url)
        if match:
            return match.group(1)
        return "unknown"

    def get_posts_from_category(self, category_url: str,
                                num_posts: int = config.DEFAULT_POSTS_PER_CATEGORY) -> List[Tuple[str, str]]:
        """
        Get post URLs from a category page using Selenium

        Args:
            category_url: URL of the category page
            num_posts: Number of posts to retrieve

        Returns:
            List of tuples (post_url, category_name)
        """
        self._init_driver()

        category_name = self.get_category_name(category_url)
        posts = []
        seen_urls = set()

        logger.info(f"Crawling category with Selenium: {category_name} ({category_url})")

        try:
            # Load the page
            self.driver.get(category_url)
            time.sleep(2)  # Wait for initial page load

            click_count = 0
            max_clicks = 10  # Maximum number of times to click "Load More"
            no_new_posts_count = 0

            while len(posts) < num_posts and click_count < max_clicks:
                # Extract posts from current page state
                new_posts = self._extract_post_urls(category_url, category_name, seen_urls)

                if new_posts:
                    posts.extend(new_posts)
                    logger.info(f"Found {len(new_posts)} new posts, total: {len(posts)}")
                    no_new_posts_count = 0
                else:
                    no_new_posts_count += 1
                    logger.debug(f"No new posts found (attempt {no_new_posts_count})")

                # Stop if we have enough posts
                if len(posts) >= num_posts:
                    break

                # Stop if no new posts found multiple times
                if no_new_posts_count >= 2:
                    logger.warning("No new posts after multiple attempts, stopping")
                    break

                # Try to click "Load More" button
                if not self._click_load_more():
                    logger.info("No more 'Load More' button found, stopping")
                    break

                click_count += 1
                time.sleep(1.5)  # Wait for content to load

            logger.info(f"Finished crawling {category_name}, collected {len(posts)} posts")

        except Exception as e:
            logger.error(f"Error crawling category {category_url}: {e}")

        return posts[:num_posts]

    def _extract_post_urls(self, base_url: str, category_name: str, seen_urls: set) -> List[Tuple[str, str]]:
        """Extract post URLs from current page state"""
        posts = []

        # Get page source and parse with BeautifulSoup
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')

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

        if re.search(r'trang-\d+\.htm$', url):
            return False

        # Should have post ID pattern
        if re.search(r'-\d+\.htm$', url):
            return True

        return False

    def _click_load_more(self) -> bool:
        """
        Try to click the 'Load More' button

        Returns:
            True if button was clicked, False otherwise
        """
        try:
            # Scroll to bottom to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

            # Try multiple selectors for the "Load More" button
            selectors = [
                (By.CSS_SELECTOR, 'a.view-more'),
                (By.XPATH, "//a[contains(text(), 'Xem thêm')]"),
                (By.XPATH, "//a[contains(@class, 'view-more')]"),
                (By.CSS_SELECTOR, '.box-viewmore a'),
            ]

            for by, selector in selectors:
                try:
                    # Wait for element to be present
                    element = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((by, selector))
                    )

                    # Check if element is visible
                    if not element.is_displayed():
                        continue

                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.3)

                    # Try to click
                    try:
                        element.click()
                        logger.debug(f"Clicked 'Load More' button using selector: {selector}")
                        return True
                    except ElementClickInterceptedException:
                        # Try JavaScript click
                        self.driver.execute_script("arguments[0].click();", element)
                        logger.debug(f"Clicked 'Load More' button via JavaScript using selector: {selector}")
                        return True

                except (TimeoutException, NoSuchElementException):
                    continue

            return False

        except Exception as e:
            logger.debug(f"Could not click 'Load More' button: {e}")
            return False

    def __enter__(self):
        """Context manager entry"""
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
