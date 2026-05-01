"""
Core scraper class for MRO Web Scraper
CLEAN VERSION - No fancy stuff, just what works
"""

import requests
import time
import random
import urllib3
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from src.models import ScraperConfig, Article
from src.utils import (
    setup_logging,
    compile_keyword_pattern,
    check_robots
)
from config.settings import MAX_ARTICLES_PER_SITE


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class MROScraper:
    """Simple scraper - just works"""
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.session = requests.Session()
        self.logger = setup_logging()
        self.keyword_pattern = compile_keyword_pattern(self.config.KEYWORDS)
        
        # Basic headers only
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _fetch_page(self, url: str, ignore_robots: bool = False) -> Optional[BeautifulSoup]:
        """Fetch page - simple retry logic"""
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                # Rotate user agent
                self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                
                # Short delay between retries
                if attempt > 0:
                    time.sleep(2 * attempt)
                
                response = self.session.get(
                    url, 
                    timeout=30,  # Longer timeout
                    allow_redirects=True,
                    verify=False,
                )
                
                # Fix encoding
                if response.encoding and response.apparent_encoding:
                    response.encoding = response.apparent_encoding
                
                # Handle 403 - retry immediately with different UA
                if response.status_code == 403:
                    self.logger.warning(f"403 on attempt {attempt + 1}, retrying...")
                    continue
                
                if response.status_code != 200:
                    self.logger.warning(f"HTTP {response.status_code} on attempt {attempt + 1}")
                    continue
                
                return BeautifulSoup(response.content, 'html.parser')
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:60]}")
                time.sleep(2)
                
        return None
    
    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links - simple approach"""
        links = set()
        domain = urlparse(base_url).netloc
        
        # Get ALL links from the page
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            
            # Only same-domain links
            if domain in full_url and full_url != base_url:
                # Filter duplicates and non-article URLs
                if not any(skip in full_url.lower() for skip in [
                    '#', 'javascript:', 'mailto:', '.jpg', '.png', '.pdf',
                    'login', 'subscribe', 'author', 'category', 'tag'
                ]):
                    links.add(full_url)
        
        self.logger.info(f"Extracted {len(links)} total links from page")
        return list(links)[:MAX_ARTICLES_PER_SITE * 2]
    
    def _extract_article_content(self, url: str, soup: BeautifulSoup) -> Optional[Article]:
        """Extract article content"""
        domain = urlparse(url).netloc.replace('www.', '')
        
        # Get title
        title = None
        for selector in ['h1', 'title', '[property="og:title"]', '.entry-title', '.post-title']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get('content', '') if selector == '[property="og:title"]' else elem.get_text()
                title = title.strip()
                if title and len(title) > 10:
                    break
        
        if not title:
            return None
        
        # Get all text
        body = soup.find('body')
        if body:
            for tag in body(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            full_text = body.get_text(separator=' ', strip=True)
        else:
            full_text = soup.get_text(separator=' ', strip=True)
        
        # Check keywords
        text_to_search = f"{title} {full_text[:3000]}"
        matched = self.keyword_pattern.findall(text_to_search)
        matched_keywords = list(set(matched))
        
        if not matched_keywords:
            return None
        
        # Get date
        pub_date = None
        time_elem = soup.find('time')
        if time_elem:
            pub_date = time_elem.get('datetime') or time_elem.get_text(strip=True)
        
        # Summary
        meta = soup.select_one('[name="description"]')
        summary = meta.get('content', '') if meta else full_text[:300]
        
        return Article(
            url=url,
            title=title[:200],
            source_domain=domain,
            publication_date=pub_date,
            summary=summary[:500],
            full_text=full_text[:5000],
            matched_keywords=matched_keywords
        )
    
    def scrape_site(self, base_url: str, ignore_robots: bool = False) -> List[Article]:
        """Scrape one site"""
        articles = []
        self.logger.info(f"\n{'='*50}\nScraping: {base_url}\n{'='*50}")
        
        # Fetch main page
        soup = self._fetch_page(base_url)
        if not soup:
            self.logger.error(f"Could not access {base_url}")
            return articles
        
        # Get article links
        article_urls = self._extract_article_links(soup, base_url)
        
        if not article_urls:
            self.logger.warning(f"No article links found on {base_url}")
            # Try to get any links at all
            self.logger.info("Trying alternative extraction...")
            for a in soup.find_all('a', href=True)[:20]:
                self.logger.info(f"  Link: {a.get('href')[:100]}")
        
        self.logger.info(f"Processing {min(len(article_urls), MAX_ARTICLES_PER_SITE)} articles...")
        
        for i, url in enumerate(article_urls[:MAX_ARTICLES_PER_SITE]):
            self.logger.info(f"[{i+1}/{min(len(article_urls), MAX_ARTICLES_PER_SITE)}] {url[:100]}")
            
            # Short delay
            time.sleep(random.uniform(1, 3))
            
            article_soup = self._fetch_page(url)
            if not article_soup:
                continue
            
            article = self._extract_article_content(url, article_soup)
            if article:
                articles.append(article)
                self.logger.info(f" {article.title[:60]}...")
                self.logger.info(f"Keywords: {article.matched_keywords}")
        
        return articles
    
    def scrape_all(self, urls: List[str], force_ignore_robots: bool = False) -> List[Article]:
        """Scrape all sites"""
        all_articles = []
        
        for url in urls:
            articles = self.scrape_site(url)
            all_articles.extend(articles)
            self.logger.info(f"\n {url}: {len(articles)} articles\n")
            time.sleep(random.uniform(2, 4))
        
        return all_articles
