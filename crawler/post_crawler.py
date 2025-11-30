"""
Module for crawling individual post pages
"""

import re
import logging
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

import config
from utils.helpers import (
    make_request, clean_text, extract_post_id_from_url,
    make_absolute_url, format_date
)

logger = logging.getLogger(__name__)


class PostCrawler:
    """Crawls individual post pages to extract content"""
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
    
    def crawl_post(self, post_url: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Crawl a single post and extract all information
        
        Args:
            post_url: URL of the post
            category: Category name
            
        Returns:
            Dictionary with post data or None if failed
        """
        logger.info(f"Crawling post: {post_url}")
        
        response = make_request(post_url, self.session)
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'lxml')
        post_id = extract_post_id_from_url(post_url)
        
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        author = self._extract_author(soup)
        date = self._extract_date(soup)
        images = self._extract_images(soup, post_url)
        audio = self._extract_audio(soup, post_url)
        reactions = self._extract_reactions(soup)
        
        return {
            'postId': post_id,
            'url': post_url,
            'title': title,
            'content': content,
            'author': author,
            'date': date,
            'category': category,
            'images': images,
            'audio': audio,
            'reactions': reactions
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract post title"""
        selectors = [
            'h1.detail-title',
            'h1.article-title',
            'h1[data-role="title"]',
            '.detail-title h1',
            'article h1',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return clean_text(element.get_text())
        
        meta = soup.find('meta', property='og:title')
        if meta:
            return clean_text(meta.get('content', ''))
        
        return ""
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract post content/body"""
        content_parts = []
        
        # Extract description/sapo
        sapo_selectors = [
            'h2.detail-sapo',
            '.detail-sapo',
            '.article-sapo',
            '.sapo',
            'p.lead'
        ]
        for selector in sapo_selectors:
            sapo = soup.select_one(selector)
            if sapo:
                content_parts.append(clean_text(sapo.get_text()))
                break
        
        # Extract main content
        content_selectors = [
            '.detail-content',
            '.detail-content-body',
            '#main-detail-body',
            '.article-content',
            'article .content',
            '[data-role="content"]'
        ]
        
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                paragraphs = content_div.find_all(['p', 'div'], recursive=False)
                for p in paragraphs:
                    if self._is_content_element(p):
                        text = clean_text(p.get_text())
                        if text and len(text) > 20:
                            content_parts.append(text)
                
                if not content_parts:
                    content_parts.append(clean_text(content_div.get_text()))
                break
        
        return '\n\n'.join(content_parts)
    
    def _is_content_element(self, element) -> bool:
        """Check if element is actual content (not ad, caption, etc.)"""
        classes = element.get('class', [])
        class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
        
        skip_patterns = ['caption', 'ad', 'relate', 'author', 'source', 'tag', 'widget']
        for pattern in skip_patterns:
            if pattern in class_str.lower():
                return False
        
        return True
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author name"""
        selectors = [
            '.detail-author',
            '.author-name',
            '.article-author',
            '[data-role="author"]',
            '.author',
            '.detail-content-author'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return clean_text(element.get_text())
        
        meta = soup.find('meta', {'name': 'author'})
        if meta:
            return clean_text(meta.get('content', ''))
        
        return "Tuổi Trẻ"
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date"""
        selectors = [
            '.detail-time',
            '.date-time',
            '.article-date',
            'time',
            '[data-role="publishdate"]',
            '.detail-content-info .date'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.has_attr('datetime'):
                    return format_date(element['datetime'])
                return format_date(element.get_text())
        
        meta = soup.find('meta', property='article:published_time')
        if meta:
            return format_date(meta.get('content', ''))
        
        return ""
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from post"""
        images = []
        seen = set()
        
        content_areas = soup.select('.detail-content, .article-content, article')
        
        for area in content_areas:
            for img in area.find_all('img'):
                src = img.get('data-src') or img.get('src') or img.get('data-original')
                if src and self._is_valid_image(src):
                    url = make_absolute_url(base_url, src)
                    if url not in seen:
                        seen.add(url)
                        images.append(url)
        
        for picture in soup.select('.detail-content picture, article picture'):
            source = picture.find('source')
            if source:
                srcset = source.get('srcset', '')
                if srcset:
                    src = srcset.split()[0]
                    url = make_absolute_url(base_url, src)
                    if url not in seen:
                        seen.add(url)
                        images.append(url)
        
        return images
    
    def _is_valid_image(self, src: str) -> bool:
        """Check if image URL is valid content image"""
        if not src:
            return False
        
        skip_patterns = ['icon', 'logo', 'avatar', 'placeholder', 'lazy', 'pixel', 
                         'transparent', '1x1', 'data:image', 'base64']
        src_lower = src.lower()
        for pattern in skip_patterns:
            if pattern in src_lower:
                return False
        
        return True
    
    def _extract_audio(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract audio/podcast URL"""
        audio = soup.find('audio')
        if audio:
            source = audio.find('source')
            if source:
                src = source.get('src')
                if src:
                    return make_absolute_url(base_url, src)
            src = audio.get('src')
            if src:
                return make_absolute_url(base_url, src)
        
        podcast_selectors = [
            '.podcast-player audio source',
            '.audio-player source',
            '[data-audio-src]',
            'a[href$=".mp3"]'
        ]
        
        for selector in podcast_selectors:
            element = soup.select_one(selector)
            if element:
                src = element.get('src') or element.get('data-audio-src') or element.get('href')
                if src:
                    return make_absolute_url(base_url, src)
        
        return None
    
    def _extract_reactions(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Extract vote/reaction counts"""
        reactions = {}
        
        reaction_selectors = [
            '.emotion-bar .emotion-item',
            '.reactions .reaction-item',
            '.vote-item',
            '[data-reaction]'
        ]
        
        for selector in reaction_selectors:
            items = soup.select(selector)
            for item in items:
                reaction_type = item.get('data-reaction') or item.get('data-type')
                if not reaction_type:
                    classes = item.get('class', [])
                    for cls in classes:
                        if any(r in cls.lower() for r in ['like', 'love', 'angry', 'sad', 'wow', 'haha']):
                            reaction_type = cls
                            break
                
                if reaction_type:
                    count_elem = item.find('.count') or item.find('span')
                    count = 0
                    if count_elem:
                        try:
                            count = int(re.sub(r'\D', '', count_elem.get_text()) or 0)
                        except ValueError:
                            pass
                    reactions[reaction_type] = count
        
        return reactions