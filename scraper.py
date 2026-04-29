"""
Core scraper class for MRO Web Scraper
Handles all fetching, parsing, and article extraction logic
"""

import requests
import time
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from src.models import ScraperConfig, Article
from src.utils import setup_logging, compile_keyword_pattern, check_robots
from config.settings import MAX_ARTICLES_PER_SITE


class MROScraper:
    """Main scraper class with robots.txt compliance and error handling"""
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.config.USER_AGENT})
        self.logger = setup_logging()
        self.keyword_pattern = compile_keyword_pattern(self.config.KEYWORDS)
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page content with retry logic"""
        if not check_robots(url, self.config.USER_AGENT, self.config.ROBOTS_CACHE):
            self.logger.warning(f"robots.txt disallows: {url}")
            return None
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = self.session.get(
                    url, 
                    timeout=self.config.REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Check for paywall/cookie wall indicators
                if "subscribe" in response.url.lower() or "paywall" in response.text.lower()[:1000]:
                    self.logger.warning(f"Possible paywall detected at {url}")
                    return None
                
                return BeautifulSoup(response.content, 'html.parser')
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.REQUEST_DELAY * (attempt + 1))
                    
        self.logger.error(f"Failed to fetch {url} after {self.config.MAX_RETRIES} attempts")
        return None
    
    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract article links from listing pages"""
        links = set()
        
        selectors = [
            'article a', '.article a', '.post a', '.entry-title a',
            'h2 a', 'h3 a', 'h4 a', '.headline a', '.title a',
            '[class*="article"] a', '[class*="post"] a', '[class*="news"] a'
        ]
        
        for selector in selectors:
            for element in soup.select(selector):
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if any(pattern in full_url.lower() for pattern in ['/news/', '/article/', '/202', '/mro-']):
                        links.add(full_url)
        
        # Fallback: find all links that look like articles
        if not links:
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                if any(p in full_url.lower() for p in ['/news/', '/article/', '/2024/', '/2025/', '/mro-']):
                    links.add(full_url)
        
        return list(links)[:MAX_ARTICLES_PER_SITE * 2]
    
    def _extract_article_content(self, url: str, soup: BeautifulSoup) -> Optional[Article]:
        """Extract structured article data from page"""
        domain = urlparse(url).netloc.replace('www.', '')
        
        # Extract title
        title = None
        for selector in ['h1', '.article-title', '.entry-title', '.post-title', '[property="og:title"]']:
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
        for selector in ['time[datetime]', '[property="article:published_time"]', '.date', '.published']:
            elem = soup.select_one(selector)
            if elem:
                pub_date = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                if pub_date:
                    break
        
        # Extract content text
        full_text = ""
        for selector in ['article', '.article-content', '.entry-content', '.post-content', 'main']:
            content_elem = soup.select_one(selector)
            if content_elem:
                for tag in content_elem(['script', 'style', 'nav', 'header', 'footer', 'aside']):
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
    
    def scrape_site(self, base_url: str) -> List[Article]:
        """Scrape a single site for relevant articles"""
        articles = []
        self.logger.info(f"Scraping: {base_url}")
        
        soup = self._fetch_page(base_url)
        if not soup:
            return articles
        
        article_urls = self._extract_article_links(soup, base_url)
        self.logger.info(f"Found {len(article_urls)} potential article links")
        
        for url in article_urls[:MAX_ARTICLES_PER_SITE]:
            self.logger.info(f"Processing: {url}")
            
            article_soup = self._fetch_page(url)
            if not article_soup:
                continue
            
            article = self._extract_article_content(url, article_soup)
            if article:
                articles.append(article)
                self.logger.info(f"Found: {article.title[:50]}...")
            
            time.sleep(self.config.REQUEST_DELAY)
        
        return articles
    
    def scrape_all(self, urls: List[str]) -> List[Article]:
        """Scrape multiple sites and return all relevant articles"""
        all_articles = []
        
        for url in urls:
            try:
                articles = self.scrape_site(url)
                all_articles.extend(articles)
                self.logger.info(f"Completed {url}: {len(articles)} articles found")
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
            
            time.sleep(self.config.REQUEST_DELAY * 2)
        
        return all_articles
