"""
Core scraper class for MRO Web Scraper
Enhanced with site-specific extraction logic and proper encoding handling
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


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class MROScraper:
    """Main scraper class with site-specific extraction and anti-blocking"""
    
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
        
        if not ignore_robots:
            if not check_robots(url, self.session.headers['User-Agent'], self.config.ROBOTS_CACHE):
                self.logger.warning(f"robots.txt disallows: {url}")
                return None
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                self._update_session_headers()
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(
                    url, 
                    timeout=self.config.REQUEST_TIMEOUT,
                    allow_redirects=True,
                    verify=False,
                )
                
                # Force proper encoding
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if response.status_code == 403:
                    self.logger.warning(f"Got 403 Forbidden on attempt {attempt + 1}")
                    if attempt < self.config.MAX_RETRIES - 1:
                        time.sleep(random.uniform(3, 5))
                        continue
                    else:
                        return None
                
                response.raise_for_status()
                
                if "subscribe" in response.url.lower() or "paywall" in response.text.lower()[:1000]:
                    self.logger.warning(f"Possible paywall detected at {url}")
                    return None
                
                return BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                
            except requests.exceptions.SSLError:
                self.logger.warning(f"SSL Error on attempt {attempt + 1}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(random.uniform(3, 5))
                    continue
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                if attempt < self.config.MAX_RETRIES - 1:
                    wait_time = self.config.REQUEST_DELAY * (attempt + 1) * random.uniform(1, 2)
                    time.sleep(wait_time)
                    
        self.logger.error(f"Failed to fetch {url}")
        return None
    
    def _extract_all_links_from_page(self, soup: BeautifulSoup, base_url: str, domain: str) -> List[str]:
        """Extract ALL links from page as fallback method"""
        links = set()
        
        # Get all anchor tags
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            
            # Only keep links from same domain
            if domain in full_url:
                # Filter for article-like URLs
                if any(pattern in full_url.lower() for pattern in [
                    '/2024/', '/2025/', '/2026/', '/news/', '/article/',
                    '/mro/', '/maintenance/', '/aviation/', '/aircraft/',
                    '/engine/', '/repair/', '/overhaul/'
                ]):
                    links.add(full_url)
        
        # If no article-specific links, get all internal links as fallback
        if not links:
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                if domain in full_url and full_url != base_url:
                    links.add(full_url)
        
        return list(links)[:MAX_ARTICLES_PER_SITE]
    
    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract article links with site-specific selectors"""
        domain = urlparse(base_url).netloc.replace('www.', '')
        links = set()
        
        # Universal selectors that work on most news sites
        universal_selectors = [
            'article a', 'a[href*="/202"]', 'a[href*="/news/"]',
            'a[href*="/article/"]', '.entry-title a', '.post-title a',
            'h2 a', 'h3 a', '.headline a', '[class*="title"] a',
            'main a', '.content a', '#content a'
        ]
        
        for selector in universal_selectors:
            try:
                for element in soup.select(selector):
                    href = element.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if domain in full_url and full_url != base_url:
                            links.add(full_url)
            except:
                continue
        
        # If universal selectors find nothing, use fallback
        if not links:
            self.logger.info(f"No links with standard selectors, using fallback method")
            links = set(self._extract_all_links_from_page(soup, base_url, domain))
        
        return list(links)[:MAX_ARTICLES_PER_SITE * 2]
    
    def _extract_article_content(self, url: str, soup: BeautifulSoup) -> Optional[Article]:
        """Extract structured article data from page"""
        domain = urlparse(url).netloc.replace('www.', '')
        
        # Extract title - try multiple methods
        title = None
        
        # Method 1: Common title selectors
        for selector in ['h1', '.article-title', '.entry-title', '.post-title', 
                        '[property="og:title"]', '.page-title', '.story-title']:
            elem = soup.select_one(selector)
            if elem:
                if selector == '[property="og:title"]':
                    title = elem.get('content', '').strip()
                else:
                    title = elem.get_text(strip=True)
                if title and len(title) > 5:
                    break
        
        # Method 2: First H1
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # Method 3: Title tag
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        if not title or title == "Untitled":
            title = f"Article from {domain}"
        
        # Extract date
        pub_date = None
        for selector in ['time[datetime]', '[property="article:published_time"]', 
                        '.date', '.published', '.post-date', 'time']:
            elem = soup.select_one(selector)
            if elem:
                pub_date = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                if pub_date:
                    break
        
        # Extract content text - get ALL text from body
        full_text = ""
        
        # Try article-specific containers first
        for selector in ['article', '.article-content', '.entry-content', 
                        '.post-content', 'main', '#content', '.content']:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove unwanted elements
                for tag in content_elem(['script', 'style', 'nav', 'header', 
                                        'footer', 'aside', 'iframe', 'noscript']):
                    tag.decompose()
                full_text = content_elem.get_text(separator=' ', strip=True)
                if len(full_text) > 100:
                    break
        
        # If still no content, get all paragraph text
        if len(full_text) < 100:
            paragraphs = soup.find_all('p')
            full_text = ' '.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
        
        # Last resort: get all body text
        if len(full_text) < 50:
            body = soup.find('body')
            if body:
                for tag in body(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    tag.decompose()
                full_text = body.get_text(separator=' ', strip=True)[:5000]
        
        # Extract summary
        meta_desc = soup.select_one('[name="description"]')
        if meta_desc and meta_desc.get('content'):
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
            title=title[:200],
            source_domain=domain,
            publication_date=pub_date,
            summary=summary[:500],
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
            self.logger.info(f"Processing: {url[:100]}...")
            
            article_soup = self._fetch_page(url, ignore_robots=ignore_robots)
            if not article_soup:
                self.logger.warning(f"Could not access article")
                continue
            
            article = self._extract_article_content(url, article_soup)
            if article:
                articles.append(article)
                self.logger.info(f" Found: {article.title[:80]}...")
            else:
                self.logger.info(f" No MRO keywords found")
            
            time.sleep(random.uniform(2, 4))
        
        return articles
    
    def scrape_all(self, urls: List[str], force_ignore_robots: bool = False) -> List[Article]:
        """Scrape multiple sites and return all relevant articles"""
        all_articles = []
        
        for url in urls:
            try:
                articles = self.scrape_site(url, ignore_robots=force_ignore_robots)
                all_articles.extend(articles)
                self.logger.info(f"Completed {url}: {len(articles)} articles")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {str(e)[:100]}")
            
            time.sleep(random.uniform(3, 6))
        
        return all_articles
