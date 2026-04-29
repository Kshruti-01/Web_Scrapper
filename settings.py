"""
Configuration settings for the MRO Web Scraper
Central place for all constants, keywords, and scraping parameters
"""

# Target URLs to scrape (excluding paywalled/blocked sites)
TARGET_URLS = [
    "https://mrobusinesstoday.com/",
    "https://www.ainonline.com/channel/maintenance",
    "https://www.aviationbusinessnews.com/mro/latest-news-mro/",
]

# Keywords for filtering (case-insensitive matching)
KEYWORDS = [
    "MRO", "maintenance", "contract", "agreement", "engine", 
    "service", "engine service", "service agreement", "repair", 
    "overhaul", "repair contract", "overhaul contract", 
    "MRO provider", "component repair", "support", "fleet support"
]

# Scraping parameters
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 15          # seconds
REQUEST_DELAY = 2.0           # seconds between requests
MAX_RETRIES = 3
MAX_ARTICLES_PER_SITE = 10    # limit to avoid overwhelming sites

# File paths (relative to project root)
EXPORT_DIR = "data/exports"
LOG_DIR = "logs"
