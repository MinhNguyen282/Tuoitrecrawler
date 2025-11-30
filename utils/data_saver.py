"""
Module for saving crawled data to JSON or YAML files
"""

import os
import json
import logging
from typing import Dict, Any

import yaml

import config

logger = logging.getLogger(__name__)


class DataSaver:
    """Handles saving post data to files"""
    
    def __init__(self, output_format: str = None):
        self.output_format = output_format or config.OUTPUT_FORMAT
    
    def save_post(self, post_data: Dict[str, Any], post_id: str) -> str:
        """Save post data to a file"""
        if self.output_format == 'yaml':
            return self._save_yaml(post_data, post_id)
        else:
            return self._save_json(post_data, post_id)
    
    def _save_json(self, data: Dict[str, Any], post_id: str) -> str:
        """Save data as JSON"""
        filepath = os.path.join(config.DATA_DIR, f"{post_id}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved JSON: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save JSON {filepath}: {e}")
            raise
    
    def _save_yaml(self, data: Dict[str, Any], post_id: str) -> str:
        """Save data as YAML"""
        filepath = os.path.join(config.DATA_DIR, f"{post_id}.yaml")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved YAML: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save YAML {filepath}: {e}")
            raise
    
    @staticmethod
    def create_post_structure(post_id: str, title: str, content: str, author: str,
                              date: str, category: str, url: str,
                              audio_url: str = None, audio_local_path: str = None,
                              image_urls: list = None, image_local_paths: list = None,
                              vote_reactions: dict = None, comments: list = None) -> Dict[str, Any]:
        """Create a standardized post data structure"""
        return {
            "postId": post_id,
            "title": title,
            "content": content,
            "author": author,
            "date": date,
            "category": category,
            "url": url,
            "audio": {
                "url": audio_url,
                "localPath": audio_local_path
            } if audio_url else None,
            "images": {
                "urls": image_urls or [],
                "localPaths": image_local_paths or []
            },
            "voteReactions": vote_reactions or {},
            "comments": comments or []
        }
    
    @staticmethod
    def create_comment_structure(comment_id: str, author: str, text: str,
                                 date: str, vote_reactions: dict = None,
                                 replies: list = None) -> Dict[str, Any]:
        """Create a standardized comment data structure"""
        return {
            "commentId": comment_id,
            "author": author,
            "text": text,
            "date": date,
            "voteReactList": vote_reactions or {},
            "commentReplies": replies or []
        }