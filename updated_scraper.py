"""
Core scraper class for MRO Web Scraper
Enhanced with human-like behavior, browser fingerprinting, and anti-detection measures
"""

import requests
import time
import random
import ssl
import urllib3
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
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


# Custom TLS Adapter to mimic Chrome's SSL fingerprint
class TLSAdapter(HTTPAdapter):
    """Custom adapter to better mimic browser TLS fingerprint"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


# Realistic browser user agents
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Mac Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class MROScraper:
    """Main scraper class with human-like behavior and anti-blocking measures"""
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.session = requests.Session()
        
        # Mount custom TLS adapter for Chrome-like fingerprint
        adapter = TLSAdapter()
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
        self.logger = setup_logging()
        self.keyword_pattern = compile_keyword_pattern(self.config.KEYWORDS)
        
        # Enable cookie persistence
        self.session.cookies.clear()
        self._initialize_cookies()
        
        self._update_session_headers()
    
    def _initialize_cookies(self):
        """Set initial cookies like a first-time visitor"""
        self.session.cookies.set('visit_count', '1')
        self.session.cookies.set('preferred_lang', 'en')
        self.session.cookies.set('tz', random.choice(['America/New_York', 'America/Chicago', 'America/Los_Angeles']))
    
    def _update_session_headers(self):
        """Update session with browser-like headers that match real Chrome"""
        user_agent = random.choice(USER_AGENTS)
        
        # Generate realistic browser fingerprint
        chrome_version = random.choice(['120', '121', '122', '123'])
        
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'en-GB,en;q=0.8,en-US;q=0.6',
                'en-US,en;q=0.9,es;q=0.8'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': random.choice(['max-age=0', 'no-cache', 'no-cache, no-store']),
            'Sec-Ch-Ua': f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}", "Not;A=Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': random.choice(['"Windows"', '"macOS"', '"Linux"']),
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'cross-site', 'same-origin']),
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        # Add realistic cookies
        if random.random() < 0.3:
            self.session.cookies.set('last_visit', str(int(time.time())))
            self.session.cookies.set('screen_res', random.choice(['1920x1080', '2560x1440', '1366x768']))
    
    def _human_behavior(self, action_type: str = "navigation"):
        """
        Simulate human behavior patterns with different delays for different actions
        """
        if action_type == "navigation":
            # Navigating to a new site (3-7 seconds)
            delay = random.uniform(3.0, 7.0)
        elif action_type == "reading":
            # Reading an article (30-90 seconds)
            delay = random.uniform(30.0, 90.0)
        elif action_type == "scrolling":
            # Scrolling through page (2-5 seconds)
            delay = random.uniform(2.0, 5.0)
        elif action_type == "click":
            # Clicking a link (0.5-2 seconds)
            delay = random.uniform(0.5, 2.0)
        elif action_type == "thinking":
            # Thinking/hesitating (1-3 seconds)
            delay = random.uniform(1.0, 3.0)
        else:
            delay = random.uniform(1.0, 3.0)
        
        self.logger.debug(f"Human behavior: {action_type} - waiting {delay:.1f}s")
        time.sleep(delay)
        
        # Occasionally take a longer break (like getting coffee)
        if random.random() < 0.1:  # 10% chance
            long_break = random.uniform(10.0, 30.0)
            self.logger.debug(f"Taking a longer break: {long_break:.1f}s")
            time.sleep(long_break)
    
    def _fetch_page(self, url: str, ignore_robots: bool = False, referer: str = None) -> Optional[BeautifulSoup]:
        """Fetch page content with realistic referrer chain and retry logic"""
        
        # Set realistic referer (where we "came from")
        if not referer:
            referer = random.choice([
                'https://www.google.com/search?q=MRO+aviation+news',
                'https://www.google.com/search?q=aircraft+maintenance+latest',
                'https://www.bing.com/search?q=MRO+industry+updates',
                'https://duckduckgo.com/?q=aviation+repair+overhaul',
                'https://www.google.com/search?q=aircraft+engine+service+agreement',
                'https://www.google.com/search?q=aviation+MRO+contracts+2026',
            ])
        
        self.session.headers['Referer'] = referer
        
        if not ignore_robots:
            if not check_robots(url, self.session.headers['User-Agent'], self.config.ROBOTS_CACHE):
                self.logger.warning(f"robots.txt disallows: {url}")
                return None
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                # Rotate browser fingerprint on each attempt
                self._update_session_headers()
                
                # Human-like thinking before request
                if attempt > 0:
                    self._human_behavior("thinking")
                
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
                        # Progressive delay with jitter
                        delay = (attempt + 1) * random.uniform(5.0, 10.0)
                        self.logger.info(f"Waiting {delay:.1f}s before retry...")
                        time.sleep(delay)
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
                    self._human_behavior("thinking")
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
        """Scrape a single site for relevant articles with human-like behavior"""
        articles = []
        self.logger.info(f"Scraping: {base_url}")
        
        # Act like we just navigated here from a search engine
        self._human_behavior("navigation")
        
        soup = self._fetch_page(base_url, ignore_robots=ignore_robots)
        if not soup:
            self.logger.warning(f"Could not access {base_url}")
            return articles
        
        # Simulate scrolling through the page
        self._human_behavior("scrolling")
        
        article_urls = self._extract_article_links(soup, base_url)
        self.logger.info(f"Found {len(article_urls)} potential article links")
        
        # Track referrer chain - we came from the main page
        referer = base_url
        
        for i, url in enumerate(article_urls[:MAX_ARTICLES_PER_SITE]):
            # Random skip (like a human deciding not to read an article)
            if random.random() < 0.15:  # 15% skip rate
                self.logger.debug(f"Skipping article (simulating human disinterest)")
                continue
            
            # Click delay - time to read headline and decide
            self._human_behavior("click")
            self._human_behavior("thinking")
            
            self.logger.info(f"Processing [{i+1}/{min(len(article_urls), MAX_ARTICLES_PER_SITE)}]: {url[:100]}...")
            
            # Pass referer to maintain browsing chain
            article_soup = self._fetch_page(url, ignore_robots=ignore_robots, referer=referer)
            
            if not article_soup:
                self.logger.warning(f"Could not access article")
                continue
            
            article = self._extract_article_content(url, article_soup)
            if article:
                articles.append(article)
                self.logger.info(f"  ✓ Found: {article.title[:80]}...")
                
                # Simulate reading time for long articles, scrolling for short ones
                if len(article.full_text) > 1000:
                    self._human_behavior("reading" if random.random() < 0.4 else "scrolling")
                else:
                    self._human_behavior("scrolling")
            else:
                self.logger.info(f"  ✗ No MRO keywords found")
        
        return articles
    
    def scrape_all(self, urls: List[str], force_ignore_robots: bool = False) -> List[Article]:
        """Scrape multiple sites with human-like delays between sites"""
        all_articles = []
        
        for i, url in enumerate(urls):
            try:
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"Site {i+1}/{len(urls)}")
                
                articles = self.scrape_site(url, ignore_robots=force_ignore_robots)
                all_articles.extend(articles)
                self.logger.info(f"✓ Completed {url}: {len(articles)} articles")
                
            except Exception as e:
                self.logger.error(f"✗ Error scraping {url}: {str(e)[:100]}")
            
            # Long break between sites (like a human finishing one site and moving to another)
            if i < len(urls) - 1:  # Don't wait after the last site
                self.logger.info("Taking a break before next site...")
                time.sleep(random.uniform(10.0, 20.0))
        
        return all_articles
