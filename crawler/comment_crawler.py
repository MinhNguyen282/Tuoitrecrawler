"""
Module for crawling comments from posts
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

import config
from utils.helpers import make_request, clean_text, get_headers

logger = logging.getLogger(__name__)


class CommentCrawler:
    """Crawls comments from posts using tuoitre's comment API"""
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
    
    def get_comments(self, post_id: str, post_url: str = None, 
                     max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Get comments for a post
        
        Args:
            post_id: The post ID
            post_url: URL of the post (for fallback HTML scraping)
            max_comments: Maximum number of comments to retrieve
            
        Returns:
            List of comment dictionaries
        """
        comments = []
        
        # Try API first
        api_comments = self._get_comments_from_api(post_id, max_comments)
        if api_comments:
            return api_comments
        
        # Fallback to HTML scraping
        if post_url:
            html_comments = self._get_comments_from_html(post_url)
            if html_comments:
                return html_comments
        
        return comments
    
    def _get_comments_from_api(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Try to get comments from tuoitre's comment API"""
        comments = []
        page = 1
        
        while len(comments) < max_comments:
            try:
                api_urls = [
                    f"https://id.tuoitre.vn/api/getlist-comment.api?objId={post_id}&objType=1&pageindex={page}&pagesize=20&sort=1",
                    f"https://tuoitre.vn/api/comment/list?id={post_id}&page={page}",
                    f"https://comment.tuoitre.vn/api/v1/comments?object_id={post_id}&page={page}&limit=20"
                ]
                
                for api_url in api_urls:
                    response = self.session.get(
                        api_url,
                        headers={
                            **get_headers(),
                            'Accept': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        timeout=config.REQUEST_TIMEOUT
                    )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            parsed = self._parse_api_response(data)
                            if parsed:
                                comments.extend(parsed)
                                if len(parsed) < 20:
                                    return comments[:max_comments]
                                break
                        except json.JSONDecodeError:
                            continue
                else:
                    break
                
                page += 1
                
            except Exception as e:
                logger.debug(f"API comment fetch failed: {e}")
                break
        
        return comments[:max_comments]
    
    def _parse_api_response(self, data: Any) -> List[Dict[str, Any]]:
        """Parse API response to extract comments"""
        comments = []
        
        if isinstance(data, dict):
            items = data.get('data') or data.get('comments') or data.get('items') or data.get('Data') or []
            if isinstance(items, dict):
                items = items.get('comments') or items.get('items') or []
        elif isinstance(data, list):
            items = data
        else:
            return []
        
        for item in items:
            comment = self._parse_comment_item(item)
            if comment:
                comments.append(comment)
        
        return comments
    
    def _parse_comment_item(self, item: Dict) -> Optional[Dict[str, Any]]:
        """Parse a single comment item from API"""
        if not item:
            return None
        
        comment_id = str(item.get('id') or item.get('commentId') or item.get('Id') or '')
        if not comment_id:
            return None
        
        author = (item.get('fullname') or item.get('author') or 
                  item.get('user_name') or item.get('FullName') or 'Anonymous')
        text = (item.get('content') or item.get('text') or 
                item.get('body') or item.get('Content') or '')
        date = (item.get('time') or item.get('date') or 
                item.get('created_at') or item.get('Time') or '')
        
        reactions = {}
        like_count = item.get('like') or item.get('likes') or item.get('Like') or 0
        if like_count:
            reactions['like'] = int(like_count)
        
        replies = []
        reply_data = item.get('reply') or item.get('replies') or item.get('children') or []
        if isinstance(reply_data, list):
            for reply_item in reply_data:
                reply = self._parse_comment_item(reply_item)
                if reply:
                    replies.append(reply)
        
        return {
            'commentId': comment_id,
            'author': clean_text(author),
            'text': clean_text(text),
            'date': str(date),
            'voteReactList': reactions,
            'commentReplies': replies
        }
    
    def _get_comments_from_html(self, post_url: str) -> List[Dict[str, Any]]:
        """Fallback: scrape comments from HTML"""
        comments = []
        
        response = make_request(post_url, self.session)
        if not response:
            return comments
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        comment_selectors = [
            '.comment-item',
            '.cmt-item',
            '[data-comment-id]',
            '.box-comment-item'
        ]
        
        comment_id_counter = 1
        for selector in comment_selectors:
            items = soup.select(selector)
            for item in items:
                comment = self._parse_html_comment(item, comment_id_counter)
                if comment:
                    comments.append(comment)
                    comment_id_counter += 1
        
        return comments
    
    def _parse_html_comment(self, element, fallback_id: int) -> Optional[Dict[str, Any]]:
        """Parse a comment from HTML element"""
        comment_id = element.get('data-comment-id') or element.get('id') or str(fallback_id)
        
        author_elem = element.select_one('.cmt-author, .comment-author, .user-name, .author')
        author = clean_text(author_elem.get_text()) if author_elem else 'Anonymous'
        
        content_elem = element.select_one('.cmt-content, .comment-content, .content, .text')
        text = clean_text(content_elem.get_text()) if content_elem else ''
        
        if not text:
            return None
        
        date_elem = element.select_one('.cmt-time, .comment-time, .date, time')
        date = clean_text(date_elem.get_text()) if date_elem else ''
        
        reactions = {}
        like_elem = element.select_one('.like-count, .likes, [data-likes]')
        if like_elem:
            try:
                like_text = like_elem.get('data-likes') or like_elem.get_text()
                reactions['like'] = int(re.sub(r'\D', '', like_text) or 0)
            except ValueError:
                pass
        
        replies = []
        reply_container = element.select_one('.replies, .sub-comments, .comment-replies')
        if reply_container:
            reply_items = reply_container.select('.comment-item, .reply-item, .cmt-item')
            for idx, reply_elem in enumerate(reply_items):
                reply = self._parse_html_comment(reply_elem, f"{comment_id}_reply_{idx}")
                if reply:
                    replies.append(reply)
        
        return {
            'commentId': str(comment_id),
            'author': author,
            'text': text,
            'date': date,
            'voteReactList': reactions,
            'commentReplies': replies
        }