"""
MRO Web Scraper - Main Entry Point
Run this script to execute the web scraping process
"""

import json
import csv
import os
from datetime import datetime
from typing import Dict, List

from src import MROScraper, ensure_export_dir
from src.models import Article
from config.settings import TARGET_URLS


def export_data(articles: List[Article], export_dir: str) -> tuple:
    """Export scraped articles to CSV and JSON formats"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    csv_filename = os.path.join(export_dir, f"mro_articles_{timestamp}.csv")
    json_filename = os.path.join(export_dir, f"mro_articles_{timestamp}.json")
    
    if articles:
        # CSV export
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=articles[0].to_dict().keys())
            writer.writeheader()
            for article in articles:
                writer.writerow(article.to_dict())
        
        # JSON export
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump([a.to_dict() for a in articles], f, indent=2, ensure_ascii=False)
    
    return csv_filename, json_filename


def generate_stats(articles: List[Article]) -> Dict:
    """Generate analytical summary of scraped data"""
    if not articles:
        return {"error": "No articles to analyze"}
    
    stats = {
        "total_articles": len(articles),
        "by_domain": {},
        "keyword_frequency": {}
    }
    
    for article in articles:
        stats["by_domain"][article.source_domain] = stats["by_domain"].get(article.source_domain, 0) + 1
        for kw in article.matched_keywords:
            stats["keyword_frequency"][kw.lower()] = stats["keyword_frequency"].get(kw.lower(), 0) + 1
    
    stats["keyword_frequency"] = dict(sorted(
        stats["keyword_frequency"].items(), 
        key=lambda x: x[1], 
        reverse=True
    ))
    
    return stats


def main():
    """Main execution function"""
    print("=" * 60)
    print("AVIATION MRO WEB SCRAPER")
    print("=" * 60)
    
    # Ensure export directory exists
    export_dir = ensure_export_dir()
    
    # Initialize and run scraper
    scraper = MROScraper()
    print(f"\nStarting scrape of {len(TARGET_URLS)} sites...")
    
    articles = scraper.scrape_all(TARGET_URLS)
    
    # Export data
    print(f"\nFound {len(articles)} relevant articles")
    
    if articles:
        csv_file, json_file = export_data(articles, export
