import sys
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import logger
from src.ingestion.pdf_processor import PDFProcessor
from src.knowledge.embedder import embedder
from src.knowledge.chroma_client import get_collection
from src.knowledge.chunker import chunker
from src.knowledge.source_registry import source_registry

console = Console()

def detect_collection(filename: str, content: str) -> str:
    text = (filename + " " + content).lower()
    if any(k in text for k in ["report", "data", "review", "index", "survey"]):
        return "market_data_reports"
    return "founders_mindsets"

def run_batch():
    pdf_dir = Path("data/knowledge_base/pdfs")
    if not pdf_dir.exists():
        pdf_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[yellow]Created {pdf_dir}. Please place PDFs there and re-run.[/yellow]")
        return

    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        console.print(f"[yellow]No PDFs found in {pdf_dir}.[/yellow]")
        return

    processor = PDFProcessor()
    total = len(pdfs)
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
        task = progress.add_task("[cyan]Processing PDFs...", total=total)

        for pdf_path in pdfs:
            source_id = source_registry.generate_source_id(str(pdf_path.name))
            
            if source_registry.is_ingested(source_id):
                progress.console.print(f"[dim]Skipping (already processed): {pdf_path.name}[/dim]")
                skipped += 1
                progress.advance(task)
                continue
                
            progress.console.print(f"[bold blue]Processing:[/bold blue] {pdf_path.name}")
            source_registry.register_source({
                "source_id": source_id,
                "source_type": "pdf",
                "source_url": str(pdf_path.name),
            })
            
            result = processor.process_pdf(str(pdf_path))
            if not result:
                progress.console.print(f"[red]Failed to process {pdf_path.name}[/red]")
                source_registry.update_status(source_id, "failed")
                progress.advance(task)
                continue
            
            collection_name = detect_collection(result["filename"], result["sections"])
            coll = get_collection(collection_name)

            meta = {
                "source": source_id,
                "filename": result["filename"],
                "total_pages": result["total_pages"],
                "key_stats_extracted": json.dumps(list(result["key_stats"])[:50]),
            }

            chunks = chunker.chunk_document(result["sections"], meta, chunk_type="report")
            
            valid_chunks = 0
            if chunks:
                progress.console.print(f"[cyan]Embedding {len(chunks)} chunks into {collection_name}...[/cyan]")
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
