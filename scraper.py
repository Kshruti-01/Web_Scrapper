"""
Core scraper class for MRO Web Scraper
Enhanced with anti-blocking measures and SSL error handling
"""

import requests
import time
import random
import urllib3
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Disable SSL warnings for sites with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from src.models import ScraperConfig, Article
from src.utils import (
    setup_logging,
    compile_keyword_pattern,
    check_robots
)
from config.settings import MAX_ARTICLES_PER_SITE


# List of real browser user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class MROScraper:
    """Main scraper class with anti-blocking and SSL error handling"""
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.session = requests.Session()
        self.logger = setup_logging()
        self.keyword_pattern = compile_keyword_pattern(self.config.KEYWORDS)
        self._update_session_headers()
    
    def _update_session_headers(self):
        """Update session with random user agent and browser-like headers"""
        user_agent = random.choice(USER_AGENTS)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def _fetch_page(self, url: str, ignore_robots: bool = False) -> Optional[BeautifulSoup]:
        """Fetch page content with retry logic, SSL handling, and anti-block measures"""
        
        # Check robots.txt (unless we're ignoring it for blocked sites)
        if not ignore_robots:
            if not check_robots(url, self.session.headers['User-Agent'], self.config.ROBOTS_CACHE):
                self.logger.warning(f"robots.txt disallows: {url}")
                return None
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                # Rotate user agent on each retry
                self._update_session_headers()
                
                # Add random delay to seem more human
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(
                    url, 
                    timeout=self.config.REQUEST_TIMEOUT,
                    allow_redirects=True,
                    verify=False,  # Skip SSL verification for problematic sites
                    headers={
                        'Referer': 'https://www.google.com/',
                    }
                )
                
                # Handle common blocks
                if response.status_code == 403:
                    self.logger.warning(f"Got 403 Forbidden, trying to bypass...")
                    # Try with different approach
                    time.sleep(random.uniform(2, 4))
                    response = self.session.get(
                        url,
                        timeout=self.config.REQUEST_TIMEOUT,
                        allow_redirects=True,
                        verify=False,
                        headers={
                            'Referer': 'https://www.bing.com/',
                            'User-Agent': random.choice(USER_AGENTS),
                        }
                    )
                
                if response.status_code == 403:
                    self.logger.warning(f"Still blocked after bypass attempt")
                    return None
                
                response.raise_for_status()
                
                # Check for paywall/cookie wall indicators
                if "subscribe" in response.url.lower() or "paywall" in response.text.lower()[:1000]:
                    self.logger.warning(f"Possible paywall detected at {url}")
                    return None
                
                return BeautifulSoup(response.content, 'html.parser')
                
            except requests.exceptions.SSLError as ssl_err:
                self.logger.warning(f"SSL Error on attempt {attempt + 1}, retrying with different approach...")
                # Try with different SSL context
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(random.uniform(3, 5))
                    continue
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    wait_time = self.config.REQUEST_DELAY * (attempt + 1) * random.uniform(1, 2)
                    time.sleep(wait_time)
                    
        self.logger.error(f"Failed to fetch {url} after {self.config.MAX_RETRIES} attempts")
        return None
    
    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract article links from listing pages"""
        links = set()
        
        selectors = [
            'article a', '.article a', '.post a', '.entry-title a',
            'h2 a', 'h3 a', 'h4 a', '.headline a', '.title a',
            '[class*="article"] a', '[class*="post"] a', '[class*="news"] a',
            'a[href*="article"]', 'a[href*="news"]', 'a[href*="202"]',
        ]
        
        for selector in selectors:
            for element in soup.select(selector):
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    # Filter only article-like URLs
                    if any(pattern in full_url.lower() for pattern in [
                        '/news/', '/article/', '/2024/', '/2025/', '/2026/',
                        '/mro-', '/maintenance', '/aviation'
                    ]):
                        links.add(full_url)
        
        # Fallback: find all links that look like articles
        if not links:
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                if any(p in full_url.lower() for p in [
                    '/news/', '/article/', '/2024/', '/2025/', '/2026/',
                    '/mro-', '/maintenance'
                ]):
                    links.add(full_url)
        
        return list(links)[:MAX_ARTICLES_PER_SITE * 2]
    
    def _extract_article_content(self, url: str, soup: BeautifulSoup) -> Optional[Article]:
        """Extract structured article data from page"""
        domain = urlparse(url).netloc.replace('www.', '')
        
        # Extract title
        title = None
        for selector in [
            'h1', '.article-title', '.entry-title', 
            '.post-title', '[property="og:title"]'
        ]:
            elem = soup.select_one(selector)
            if elem:
                if selector == '[property="og:title"]':
                    title = elem.get('content', '').strip()
                else:
                    title = elem.get_text(strip=True)
                if title:
                    break
        
        if not title:
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"
        
        # Extract date
        pub_date = None
        for selector in [
            'time[datetime]', '[property="article:published_time"]', 
            '.date', '.published'
        ]:
            elem = soup.select_one(selector)
            if elem:
                pub_date = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                if pub_date:
                    break
        
        # Extract content text
        full_text = ""
        for selector in [
            'article', '.article-content', '.entry-content', 
            '.post-content', 'main'
        ]:
            content_elem = soup.select_one(selector)
            if content_elem:
                for tag in content_elem([
                    'script', 'style', 'nav', 'header', 'footer', 'aside'
                ]):
                    tag.decompose()
                full_text = content_elem.get_text(separator=' ', strip=True)
                break
        
        if not full_text:
            paragraphs = soup.find_all('p')
            full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        # Extract summary
        meta_desc = soup.select_one('[name="description"]')
        if meta_desc:
            summary = meta_desc.get('content', '')
        else:
            summary = full_text[:300] + '...' if len(full_text) > 300 else full_text
        
        # Find matching keywords
        text_to_search = f"{title} {full_text}"
        matched = self.keyword_pattern.findall(text_to_search)
        matched_keywords = list(set(matched))
        
        if not matched_keywords:
            return None
        
        return Article(
            url=url,
            title=title,
            source_domain=domain,
            publication_date=pub_date,
            summary=summary,
            full_text=full_text[:5000],
            matched_keywords=matched_keywords
        )
    
    def scrape_site(self, base_url: str, ignore_robots: bool = False) -> List[Article]:
        """Scrape a single site for relevant articles"""
        articles = []
        self.logger.info(f"Scraping: {base_url}")
        
        soup = self._fetch_page(base_url, ignore_robots=ignore_robots)
        if not soup:
            self.logger.warning(f"Could not access {base_url}")
            return articles
        
        article_urls = self._extract_article_links(soup, base_url)
        self.logger.info(f"Found {len(article_urls)} potential article links")
        
        for url in article_urls[:MAX_ARTICLES_PER_SITE]:
            self.logger.info(f"Processing: {url}")
            
            article_soup = self._fetch_page(url, ignore_robots=ignore_robots)
            if not article_soup:
                self.logger.warning(f"Could not access article: {url}")
                continue
            
            article = self._extract_article_content(url, article_soup)
            if article:
                articles.append(article)
                self.logger.info(f"Found: {article.title[:80]}...")
            
            time.sleep(random.uniform(2, 4))
        
        return articles
    
    def scrape_all(self, urls: List[str], force_ignore_robots: bool = False) -> List[Article]:
        """Scrape multiple sites and return all relevant articles"""
        all_articles = []
        
        for url in urls:
            try:
                articles = self.scrape_site(url, ignore_robots=force_ignore_robots)
                all_articles.extend(articles)
                self.logger.info(f"Completed {url}: {len(articles)} articles found")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
            
            time.sleep(random.uniform(3, 6))
        
        return all_articles
