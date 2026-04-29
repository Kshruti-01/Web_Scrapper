"""
Utility functions for the MRO Web Scraper
Includes logging setup, keyword pattern compilation, and helper functions
"""

import re
import logging
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import List, Pattern
from config.settings import LOG_DIR, EXPORT_DIR


def setup_logging(name: str = "mro_scraper") -> logging.Logger:
    """Configure and return a logger with file and console handlers"""
    
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler with timestamp in filename
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f"scraper_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def compile_keyword_pattern(keywords: List[str]) -> Pattern:
    """Create a compiled regex pattern for all keywords"""
    escaped_keywords = [re.escape(kw) for kw in keywords]
    pattern_str = r'\b(' + '|'.join(escaped_keywords) + r')\b'
    return re.compile(pattern_str, re.IGNORECASE)


def check_robots(url: str, user_agent: str, cache: dict) -> bool:
    """Check if URL is allowed by robots.txt (with caching)"""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    if base_url in cache:
        return cache[base_url]
    
    try:
        rp = RobotFileParser()
        rp.set_url(urljoin(base_url, "/robots.txt"))
        rp.read()
        allowed = rp.can_fetch(user_agent, url)
        cache[base_url] = allowed
        return allowed
    except Exception:
        # Default to cautious: allow but log warning later
        return True


def ensure_export_dir() -> str:
    """Create export directory and return its path"""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    return EXPORT_DIR
