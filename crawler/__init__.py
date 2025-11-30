"""
Crawler modules for tuoitre.vn
"""

from .selenium_category_crawler import SeleniumCategoryCrawler as CategoryCrawler
from .post_crawler import PostCrawler
from .comment_crawler import CommentCrawler