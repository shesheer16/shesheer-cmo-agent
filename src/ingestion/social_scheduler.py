import os
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
import time

from src.knowledge.embedder import embedder
from src.knowledge.chroma_client import get_collection
from src.knowledge.source_registry import source_registry
from src.utils.logger import logger

RSS_FEEDS = {
    "zerodha": "https://zerodha.com/z-connect/feed",
    "blume": "https://blume.vc/feed",
    "inc42": "https://inc42.com/feed/"
}

def ingest_rss_feeds():
    logger.info("Starting Daily RSS Ingestion Job")
    collection = get_collection("social_intelligence")
    
    for source_name, url in RSS_FEEDS.items():
        try:
            logger.info(f"Fetching RSS feed from {source_name}")
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            
            processed = 0
            for item in items[:5]: # Take top 5 recent posts per feed
                title = item.title.text if item.title else "No Title"
                link = item.link.text if item.link else "No Link"
                desc = item.description.text if item.description else ""
                
                # Clean HTML from description
                desc_text = BeautifulSoup(desc, "html.parser").get_text(strip=True)
                
                source_id = source_registry.generate_source_id(link)
                if source_registry.is_ingested(source_id):
                    continue
                    
                content = f"Title: {title}\nSource: {source_name}\nContent: {desc_text}"
                
                source_registry.register_source({
                    "source_id": source_id,
                    "source_type": "rss",
                    "source_url": link
                })
                
                vector = embedder.embed(content)
                collection.upsert(
                    ids=[source_id],
                    documents=[content],
                    embeddings=[vector],
                    metadatas=[{"source": source_name, "title": title, "link": link}]
                )
                
                source_registry.update_status(source_id, "complete", 1)
                processed += 1
                
            logger.info(f"Ingested {processed} new items from {source_name}")
            
        except Exception as e:
            logger.error(f"Failed to ingest RSS from {source_name}: {e}")

def run_weekly_maintenance():
    logger.info("Running weekly maintenance job")
    import asyncio
    try:
        from src.utils.monitor import send_weekly_report_telegram
        asyncio.run(send_weekly_report_telegram())
    except Exception as e:
        logger.error(f"Weekly report failed: {e}")
    logger.info("Weekly maintenance completed.")


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run daily at 6am
    scheduler.add_job(ingest_rss_feeds, 'cron', hour=6, minute=0)
    # Run weekly on Sunday at 2am
    scheduler.add_job(run_weekly_maintenance, 'cron', day_of_week='sun', hour=2, minute=0)
    scheduler.start()
    logger.info("APScheduler started for Social Intelligence.")
    
if __name__ == "__main__":
    # Test run
    ingest_rss_feeds()
