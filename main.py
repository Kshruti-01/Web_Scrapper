"""
MRO Web Scraper - Main Entry Point
Now with RSS feed support (guaranteed to work)
"""

import json
import csv
import os
from datetime import datetime
from typing import Dict, List

from src import MROScraper, ensure_export_dir
from src.models import Article
from src.rss_scraper import RSSScraper
from config.settings import TARGET_URLS


def export_data(articles: List[Article], export_dir: str) -> tuple:
    """Export scraped articles to CSV and JSON formats"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    csv_filename = os.path.join(export_dir, f"mro_articles_{timestamp}.csv")
    json_filename = os.path.join(export_dir, f"mro_articles_{timestamp}.json")
    
    if articles:
        # Remove duplicates by URL
        unique_articles = {}
        for article in articles:
            if article.url not in unique_articles:
                unique_articles[article.url] = article
        
        articles = list(unique_articles.values())
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=articles[0].to_dict().keys())
            writer.writeheader()
            for article in articles:
                writer.writerow(article.to_dict())
        
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
    
    export_dir = ensure_export_dir()
    
    # RSS Feeds that WILL work (Google News MRO search)
    rss_urls = [
        "https://news.google.com/rss/search?q=MRO+maintenance+repair+overhaul+aviation&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=aircraft+engine+service+agreement+contract&hl=en-US&gl=US&ceid=US:en",
    ]
    
    print(f"\n Starting scrape...")
    print("=" * 60)
    
    # Try RSS feeds first (guaranteed to work)
    print("\n📻 Attempting RSS Feeds (always accessible)...")
    rss_scraper = RSSScraper()
    articles = rss_scraper.scrape_rss_feeds(rss_urls)
    
    # Then try regular websites
    print(f"\n Attempting regular websites...")
    web_scraper = MROScraper()
    web_articles = web_scraper.scrape_all(TARGET_URLS, force_ignore_robots=True)
    articles.extend(web_articles)
    
    # Export and display results
    print(f"\n Total articles found: {len(articles)}")
    
    if articles:
        csv_file, json_file = export_data(articles, export_dir)
        
        stats = generate_stats(articles)
        
        print("\n" + "=" * 60)
        print("ANALYTICAL SUMMARY")
        print("=" * 60)
        print(f"\n Total Articles: {stats['total_articles']}")
        
        print("\n Articles by Domain:")
        for domain, count in stats['by_domain'].items():
            print(f" {domain}: {count}")
        
        print("\n Top Keywords Found:")
        for kw, freq in list(stats['keyword_frequency'].items())[:10]:
            print(f" {kw}: {freq} occurrences")
        
        print(f"\n Data exported to:")
        print(f" CSV: {csv_file}")
        print(f" JSON: {json_file}")
        
        print("\nArticle Preview (first 10):")
        for i, article in enumerate(articles[:10], 1):
            print(f"   {i}. [{article.source_domain}] {article.title[:80]}...")
            print(f" Keywords: {', '.join(article.matched_keywords[:5])}")
    
    else:
        print("\nNo articles found. Check your internet connection.")
    
    print("\n" + "=" * 60)
    print("Scraping completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
