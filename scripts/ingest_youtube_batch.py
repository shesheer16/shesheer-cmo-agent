import sys
import json
import yaml
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import logger
from src.ingestion.youtube_ingester import YouTubeIngester
from src.knowledge.embedder import embedder
from src.knowledge.chroma_client import get_collection
from src.knowledge.chunker import chunker
from src.knowledge.source_registry import source_registry

console = Console()

def run_batch():
    yaml_path = Path("data/sources/youtube_sources.yaml")
    if not yaml_path.exists():
        console.print(f"[red]Could not find {yaml_path}[/red]")
        return
        
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
        
    sources_config = data.get("sources", [])
    if not sources_config:
        console.print("[yellow]No sources found in YAML.[/yellow]")
        return
        
    # Flatten videos
    all_videos = []
    for src in sources_config:
        videos = src.get("videos", [])
        for v in videos:
            all_videos.append({
                "url": v["url"],
                "priority": v.get("priority", 99),
                "title_override": v.get("title", ""),
                "config": src
            })
            
    all_videos.sort(key=lambda x: x["priority"])
    
    ingester = YouTubeIngester()
    total = len(all_videos)
    processed_count = 0
    skipped_count = 0
    duplicate_chunks = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing YouTube Sources...", total=total)
        
        for video in all_videos:
            url = video["url"]
            config = video["config"]
            source_id = source_registry.generate_source_id(url)
            
            if source_registry.is_ingested(source_id):
                progress.console.print(f"[dim]Skipping (already processed): {url}[/dim]")
                skipped_count += 1
                progress.advance(task)
                continue
                
            progress.console.print(f"[bold blue]Processing:[/bold blue] {url}")
            source_registry.register_source({
                "source_id": source_id,
                "source_type": "youtube",
                "source_url": url,
                "person": config.get("person", ""),
                "company": config.get("company", ""),
                "collection_name": config.get("collection", "founders_mindsets")
            })
            
            result = ingester.process_video(url)
            if not result:
                progress.console.print(f"[red]Failed to ingest {url}[/red]")
                source_registry.update_status(source_id, "failed")
                progress.advance(task)
                continue
                
            collection_name = config.get("collection", "founders_mindsets")
            
            try:
                coll = get_collection(collection_name)
            except Exception as e:
                progress.console.print(f"[red]Failed to get collection {collection_name}: {e}[/red]")
                source_registry.update_status(source_id, "failed")
                progress.advance(task)
                continue
            
            segments = result.get("segments", [])
            chunks_to_embed = []
            
            for idx, segment in enumerate(segments):
                text = segment["text"]
                topic = video["title_override"] if video["title_override"] else result['title']
                
                meta = {
                    "source": source_id,
                    "url": url,
                    "person": config.get("person", result["channel"]),
                    "company": config.get("company", ""),
                    "topic": f"{topic} - segment {idx}",
                    "year": result["date"][:4] if result.get("date") else "", 
                    "market_phase": config.get("market_phase", ""),
                    "insight_type": config.get("insight_type", ""),
                    "applicable_segment": json.dumps(config.get("applicable_segment", [])),
                    "start_time": segment["start_time"],
                    "word_count": segment["word_count"]
                }
                
                chunk_dict = chunker._create_chunk_dict(text, meta, idx, len(segments), "video_segment")
                chunks_to_embed.append(chunk_dict)
                
            if chunks_to_embed:
                progress.console.print(f"[cyan]Embedding {len(chunks_to_embed)} segments...[/cyan]")
                
                valid_chunks = 0
                for c in chunks_to_embed:
                    vector = embedder.embed(c["text"])
                    
                    # Deduplication
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
            processed_count += 1
            progress.advance(task)
            
    console.print(f"\n[bold green]Batch Complete![/bold green]")
    console.print(f"Processed: {processed_count}")
    console.print(f"Skipped: {skipped_count}")
    console.print(f"Duplicates Prevented: {duplicate_chunks}")
    console.print(f"Total: {total}")

if __name__ == "__main__":
    try:
        run_batch()
    except KeyboardInterrupt:
        console.print("\n[red]Batch processing cancelled by user.[/red]")
        sys.exit(0)
