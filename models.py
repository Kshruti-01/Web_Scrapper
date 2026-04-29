"""
Data models for the MRO Web Scraper
Defines structured containers for configuration and scraped articles
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import KEYWORDS, USER_AGENT, REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES


@dataclass
class ScraperConfig:
    """Configuration settings for the scraper"""
    USER_AGENT: str = USER_AGENT
    REQUEST_TIMEOUT: int = REQUEST_TIMEOUT
    REQUEST_DELAY: float = REQUEST_DELAY
    MAX_RETRIES: int = MAX_RETRIES
    ROBOTS_CACHE: Dict[str, bool] = field(default_factory=dict)
    KEYWORDS: List[str] = field(default_factory=lambda: KEYWORDS.copy())


@dataclass
class Article:
    """Structured data container for scraped articles"""
    url: str
    title: str
    source_domain: str
    publication_date: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    matched_keywords: List[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for CSV/JSON export"""
        d = asdict(self)
        d['matched_keywords'] = ', '.join(self.matched_keywords)
        return d
