import sys
import json
import yaml
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import logger
from src.ingestion.web_scraper import WebScraper
from src.knowledge.embedder import embedder
from src.knowledge.chroma_client import get_collection
from src.knowledge.chunker import chunker
from src.knowledge.source_registry import source_registry

console = Console()

def detect_collection(content: str, title: str) -> str:
    text = (title + " " + content).lower()
    if any(k in text for k in ["market share", "report", "cagr", "survey", "statistics", "data", "revenue"]):
        return "market_data_reports"
    return "founders_mindsets"

def run_batch():
    yaml_path = Path("data/sources/web_sources.yaml")
    if not yaml_path.exists():
        console.print(f"[red]Could not find {yaml_path}. Creating template...[/red]")
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        example = {
            "sources": [
                {
                    "name": "The Ken - EdTech Archives",
                    "collection": "market_data_reports",
                    "articles": [
                        {"url": "https://the-ken.com/story/physicswallah-unicorn/", "title": "PW Unicorn", "priority": 1}
                    ]
                }
            ]
        }
        with open(yaml_path, "w") as f:
            yaml.dump(example, f, sort_keys=False)
        console.print(f"[yellow]Created template at {yaml_path}.[/yellow]")
        sys.exit(0)
        
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
        
    sources_config = data.get("sources", [])
    
    all_articles = []
    for src in sources_config:
        articles = src.get("articles", [])
        for a in articles:
            all_articles.append({
                "url": a["url"],
                "title_override": a.get("title", ""),
                "priority": a.get("priority", 99),
                "config": src
            })
            
    all_articles.sort(key=lambda x: x["priority"])
    
    scraper = WebScraper()
    total = len(all_articles)
    processed = 0
    skipped = 0
    duplicate_chunks = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing Web Sources...", total=total)
        
        for article in all_articles:
            url = article["url"]
            config = article["config"]
            source_id = source_registry.generate_source_id(url)
            
            if source_registry.is_ingested(source_id):
                progress.console.print(f"[dim]Skipping (already processed): {url}[/dim]")
                skipped += 1
                progress.advance(task)
                continue
                
            progress.console.print(f"[bold blue]Scraping:[/bold blue] {url}")
            source_registry.register_source({
                "source_id": source_id,
                "source_type": "web",
                "source_url": url,
                "person": config.get("author", ""),
                "collection_name": config.get("collection", "")
            })
            
            result = scraper.scrape(url)
            if not result:
                progress.console.print(f"[red]Failed to scrape {url}[/red]")
                source_registry.update_status(source_id, "failed")
                progress.advance(task)
                continue
                
            collection_name = config.get("collection") or detect_collection(result["content"], result["title"])
            coll = get_collection(collection_name)
            
            meta = {
                "source": source_id,
                "url": url,
                "title": article["title_override"] if article["title_override"] else result["title"],
                "author": result["author"],
                "year": result["date"][:4] if result["date"] else "",
                "topic": "\n".join(config.get("topics", [])),
                "applicable_segment": json.dumps(config.get("applicable_segment", []))
            }
            
            chunks = chunker.chunk_document(result["content"], meta, chunk_type="article")
            
            valid_chunks = 0
            if chunks:
                progress.console.print(f"[cyan]Embedding {len(chunks)} chunks...[/cyan]")
                for c in chunks:
                    vector = embedder.embed(c["text"])
                    if source_registry.is_duplicate_chunk(collection_name, vector):
                        duplicate_chunks += 1
                        continue
                        
                    clean_meta = {}
                    for k,v in c["metadata"].items():
                        clean_meta[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
                            
                    coll.upsert(
                        ids=[c["chunk_id"]],
                        documents=[c["text"]],
                        embeddings=[vector],
                        metadatas=[clean_meta]
                    )
                    valid_chunks += 1
            
            source_registry.update_status(source_id, "complete", valid_chunks)
            processed += 1
            progress.advance(task)
            
    console.print(f"\n[bold green]Batch Complete![/bold green] Processed {processed}, Skipped {skipped}, Duplicates Prevented {duplicate_chunks}.")

if __name__ == "__main__":
    try:
        run_batch()
    except KeyboardInterrupt:
        sys.exit(0)
