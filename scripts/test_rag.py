import sys
import time
from pathlib import Path
from rich.console import Console

sys.path.append(str(Path(__file__).parent.parent))

from src.core.rag.rag_pipeline import rag_pipeline
from src.utils.logger import logger
import asyncio

console = Console()

async def test_queries():
    queries = [
        "PhysicsWallah pricing strategy",
        "Indian FMCG distribution tier 2/3",
        "Kunal Shah consumer psychology",
        "Byju's failure reasons",
        "Zerodha zero marketing growth",
        "Jio distribution strategy India",
        "Nykaa trust building India",
        "Ariel cultural tension campaign",
        "Nirma disruptive pricing",
        "Kan Khajura constraint innovation"
    ]
    
    startup_context = {"domain": "EdTech", "stage": "Pre-launch", "target": "Tier 2", "last_decision": "None"}
    
    for q in queries:
        console.print(f"\n[bold magenta]Testing Query:[/bold magenta] {q}")
        start_t = time.time()
        context_pkg = await rag_pipeline.process(q, startup_context, [])
        elapsed = time.time() - start_t
        
        console.print(f"[green]Completed in {elapsed:.2f}s[/green]")
        console.print(f"[yellow]Tokens: {context_pkg.total_tokens} | Chunks: {context_pkg.chunks_included}[/yellow]")
        
        # Print headers to verify
        lines = context_pkg.formatted_context.split('\n')
        for line in lines:
            if line.startswith("[") and "SOURCE" in line:
                console.print(f"[dim]{line}[/dim]")
            elif line.startswith("    TOPIC") or line.startswith("    APPLICABILITY"):
                console.print(f"[dim]{line}[/dim]")

if __name__ == "__main__":
    asyncio.run(test_queries())
