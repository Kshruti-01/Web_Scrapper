"""
RSS Feed Scraper for MRO News
RSS feeds are designed to be machine-readable and rarely blocked
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse
import re

from src.models import Article
from src.utils import compile_keyword_pattern, setup_logging
from config.settings import KEYWORDS


class RSSScraper:
    """Scraper specifically for RSS/XML feeds (never blocked)"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.keyword_pattern = compile_keyword_pattern(KEYWORDS)
    
    def fetch_rss_feed(self, url: str) -> Optional[ET.Element]:
        """Fetch and parse an RSS feed"""
        try:
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; MRO-Scraper/1.0)'
            })
            response.raise_for_status()
            return ET.fromstring(response.content)
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS feed {url}: {e}")
            return None
    
    def extract_articles_from_rss(self, root: ET.Element, feed_url: str) -> List[Article]:
        """Extract articles from RSS XML"""
        articles = []
        domain = urlparse(feed_url).netloc
        
        # RSS 2.0 format
        for item in root.findall('.//item'):
            try:
                title = item.find('title').text if item.find('title') is not None else "No title"
                link = item.find('link').text if item.find('link') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else None
                
                # Clean HTML from description
                clean_desc = re.sub(r'<[^>]+>', '', description) if description else ""
                
                # Check for keywords
                text_to_search = f"{title} {clean_desc}"
                matched = self.keyword_pattern.findall(text_to_search)
                matched_keywords = list(set(matched))
                
                if matched_keywords:
                    article = Article(
                        url=link,
                        title=title[:200],
                        source_domain=domain,
                        publication_date=pub_date,
                        summary=clean_desc[:500],
                        full_text=clean_desc[:5000],
                        matched_keywords=matched_keywords
                    )
                    articles.append(article)
                    
            except Exception as e:
                self.logger.warning(f"Error parsing RSS item: {e}")
                continue
        
        return articles
    
    def scrape_rss_feeds(self, urls: List[str]) -> List[Article]:
        """Scrape multiple RSS feeds"""
        all_articles = []
        
        for url in urls:
            self.logger.info(f"Fetching RSS: {url}")
            root = self.fetch_rss_feed(url)
            
            if root:
                articles = self.extract_articles_from_rss(root, url)
                all_articles.extend(articles)
                self.logger.info(f"Found {len(articles)} articles from RSS")
        
        return all_articles
