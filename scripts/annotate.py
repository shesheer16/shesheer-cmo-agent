import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from src.knowledge.chunker import chunker
from src.knowledge.chroma_client import get_collection
from src.knowledge.embedder import embedder

console = Console()
ANNOTATIONS_DIR = Path("data/annotations")
ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

MARKET_PHASES = ["0_to_1", "1_to_10", "10_to_100", "scale"]
INSIGHT_TYPES = ["pricing", "distribution", "brand", "growth", "retention", "fundraising", "team", "product", "market_timing", "trust"]
SEGMENTS = ["india1", "india2", "india3", "urban", "rural", "b2b", "b2c", "d2c"]

def dropdown_prompt(title, options):
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    for i, opt in enumerate(options, 1):
        console.print(f"  [green]{i}.[/green] {opt}")
    
    while True:
        choice = Prompt.ask(f"Select option (1-{len(options)})")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        console.print("[red]Invalid selection.[/red]")

def multi_select_prompt(title, options):
    console.print(f"\n[bold cyan]{title}[/bold cyan] (comma separated numbers)")
    for i, opt in enumerate(options, 1):
        console.print(f"  [green]{i}.[/green] {opt}")
    
    while True:
        choices = Prompt.ask("Select options (e.g., 1,3,4)")
        if not choices.strip():
            return []
        parts = [p.strip() for p in choices.split(",")]
        selected = []
        valid = True
        for p in parts:
            if p.isdigit() and 1 <= int(p) <= len(options):
                selected.append(options[int(p)-1])
            else:
                valid = False
        if valid:
            return selected
        console.print("[red]Invalid selection. Use comma separated numbers.[/red]")


def run_cli():
    console.print(Panel.fit("[bold magenta]Shesheer CMO Agent - Annotation CLI[/bold magenta]"))
    
    action = dropdown_prompt("Action", ["Create New Annotation", "Edit Existing Annotation"])
    
    data = {}
    if action == "Edit Existing Annotation":
        files = list(ANNOTATIONS_DIR.glob("*.json"))
        if not files:
            console.print("[red]No annotations found to edit.[/red]")
            return
        
        file_opts = [f.stem for f in files]
        source_id = dropdown_prompt("Select annotation to edit", file_opts)
        
        with open(ANNOTATIONS_DIR / f"{source_id}.json", "r") as f:
            data = json.load(f)
            
        console.print(f"\n[green]Loaded annotation: {source_id}[/green]")
    else:
        source_id = Prompt.ask("\n[bold cyan]source_id[/bold cyan] (unique identifier, e.g., pw-affordability)")
        data["source_id"] = source_id

    # Gather fields with defaults
    data["person_brand"] = Prompt.ask("\n[bold cyan]person/brand[/bold cyan]", default=data.get("person_brand", ""))
    data["company"] = Prompt.ask("\n[bold cyan]company[/bold cyan]", default=data.get("company", ""))
    data["topic"] = Prompt.ask("\n[bold cyan]topic[/bold cyan]", default=data.get("topic", ""))
    
    console.print(f"\nCurrent market_phase: {data.get('market_phase', 'None')}")
    if Confirm.ask("Change market_phase?", default=(not bool(data.get("market_phase")))):
        data["market_phase"] = dropdown_prompt("market_phase", MARKET_PHASES)
        
    console.print(f"\nCurrent insight_type: {data.get('insight_type', 'None')}")
    if Confirm.ask("Change insight_type?", default=(not bool(data.get("insight_type")))):
        data["insight_type"] = dropdown_prompt("insight_type", INSIGHT_TYPES)
        
    console.print(f"\nCurrent applicable_segment: {data.get('applicable_segment', [])}")
    if Confirm.ask("Change applicable_segment?", default=(not bool(data.get("applicable_segment")))):
        data["applicable_segment"] = multi_select_prompt("applicable_segment", SEGMENTS)
        
    data["key_belief"] = Prompt.ask("\n[bold cyan]key_belief[/bold cyan]", default=data.get("key_belief", ""))
    data["outcome"] = Prompt.ask("\n[bold cyan]outcome[/bold cyan]", default=data.get("outcome", ""))
    
    contradicts = Confirm.ask("\n[bold cyan]contradicts_western framework?[/bold cyan]", default=bool(data.get("contradicts_western")))
    if contradicts:
        data["contradicts_western"] = Prompt.ask("Explain what and why", default=data.get("contradicts_western") if isinstance(data.get("contradicts_western"), str) else "")
    else:
        data["contradicts_western"] = False

    console.print(f"\nCurrent tags: {data.get('tags', [])}")
    tags_str = Prompt.ask("\n[bold cyan]tags[/bold cyan] (comma separated)", default=",".join(data.get("tags", [])))
    data["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    data["content"] = Prompt.ask("\n[bold cyan]content[/bold cyan]", default=data.get("content", ""))

    # Save
    file_path = ANNOTATIONS_DIR / f"{data['source_id']}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    console.print(f"\n[bold green]Saved to {file_path}[/bold green]")

    # Preview Chunking
    console.print("\n[bold magenta]Chunking Preview:[/bold magenta]")
    
    # We pass the entire dictionary to chunk_document, which will keep it together as a single structural chunk
    metadata = data.copy()
    metadata["source"] = data.get("source_id") # Map for ID generation
    
    # Package as list of dicts to trigger JSON parsing logic in chunker
    json_rep = json.dumps([data]) 
    chunks = chunker.chunk_document(json_rep, metadata, chunk_type="annotation")
    
    table = Table(title="Chunks generated")
    table.add_column("Chunk ID", style="cyan")
    table.add_column("Tokens", style="magenta")
    table.add_column("Metadata Keys", style="green")
    
    for c in chunks:
        tokens = chunker.get_token_count(c["text"])
        table.add_row(c["chunk_id"], str(tokens), str(list(c["metadata"].keys())))
    console.print(table)

    # Embed & Store
    if Confirm.ask("\n[bold yellow]Embed and store in ChromaDB now?[/bold yellow]"):
        # Basic logic to route to correct collection
        target_collection = "founders_mindsets"
        if data.get("insight_type") in ["brand", "distribution", "pricing"]:
            target_collection = "campaign_case_studies"
            
        coll = get_collection(target_collection)
        
        with console.status("Embedding chunks..."):
            for c in chunks:
                vector = embedder.embed(c["text"])
                # Convert complex metadata types to string for ChromaDB
                clean_meta = {}
                for k,v in c["metadata"].items():
                    if isinstance(v, (list, dict)):
                        clean_meta[k] = json.dumps(v)
                    elif isinstance(v, bool):
                        clean_meta[k] = str(v)
                    else:
                        clean_meta[k] = v
                        
                coll.upsert(
                    ids=[c["chunk_id"]],
                    documents=[c["text"]],
                    embeddings=[vector],
                    metadatas=[clean_meta]
                )
        console.print(f"[bold green]Successfully embedded into ChromaDB collection '{target_collection}'![/bold green]")

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        console.print("\n[red]Annotation cancelled.[/red]")
        sys.exit(0)
