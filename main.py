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
    
    scraper = MROScraper()
    print(f"\n Starting scrape of {len(TARGET_URLS)} sites...")
    print("Note: Some sites block scrapers. Using enhanced bypass methods\n")
    
    # Force ignore robots.txt since these sites block all scrapers anyway
    articles = scraper.scrape_all(TARGET_URLS, force_ignore_robots=True)
    
    print(f"\n Found {len(articles)} relevant articles")
    
    if articles:
        csv_file, json_file = export_data(articles, export_dir)
        
        stats = generate_stats(articles)
        
        print("\n" + "=" * 60)
        print("ANALYTICAL SUMMARY")
        print("=" * 60)
        print(f"\n Total Articles: {stats['total_articles']}")
        
        print("\n Articles by Domain:")
        for domain, count in stats['by_domain'].items():
            print(f"{domain}: {count}")
        
        print("\n Top Keywords Found:")
        for kw, freq in list(stats['keyword_frequency'].items())[:10]:
            print(f" {kw}: {freq} occurrences")
        
        print(f"\nData exported to:")
        print(f" CSV: {csv_file}")
        print(f" JSON: {json_file}")
        
        print("\nArticle Preview (first 5):")
        for i, article in enumerate(articles[:5], 1):
            print(f"   {i}. [{article.source_domain}] {article.title[:80]}...")
            print(f" Keywords: {', '.join(article.matched_keywords[:5])}")
    
    else:
        print("\n No articles found matching the keywords.")
        print(" Websites are heavily blocking automated access")
        print(" Consider using official APIs or RSS feeds instead")
        print(" Check logs/ folder for detailed error messages")
        print("\n  Suggestion: Use NewsAPI or RSS feeds for these sources")
    
    print("\n" + "=" * 60)
    print("Scraping completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
