import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from rich.console import Console
from rich.panel import Panel
from src.agent import ShesheerCMOAgent

console = Console()

async def test_reasoning():
    # Example startup context
    startup_context = {
        "domain": "Test Prep App (JEE/NEET)",
        "stage": "Seed Funded (₹3 Cr), 5000 MAU",
        "target_audience": "Class 11-12 students in Tier 2/3 cities (UP, Bihar, MP)",
        "current_challenge": "Customer acquisition cost on Instagram is too high. Considering hiring 5 mid-tier influencers for a brand awareness campaign."
    }
    
    agent = ShesheerCMOAgent(startup_context=startup_context)
    
    query = "Should I hire influencers for my Tier 2 test prep app to bring down my CAC?"
    
    console.print(f"[bold cyan]Founder Query:[/bold cyan] {query}\n")
    console.print(f"[dim]Running RAG Pipeline + Reasoning Engine...[/dim]\n")
    
    memo = await agent.ask(query)
    
    console.print(Panel(memo, title="Strategic Memo (Indian CMO)", border_style="green"))
    
    # Validate structure
    required_sections = [
        "SITUATION ANALYSIS", 
        "INDIAN MARKET PRECEDENT", 
        "THE MOVE", 
        "THE TRAP TO AVOID", 
        "THE QUESTION YOU HAVEN'T ASKED"
    ]
    
    missing = [s for s in required_sections if s not in memo]
    if missing:
        console.print(f"\n[bold red]Validation Failed![/bold red] Missing sections: {missing}")
    else:
        console.print("\n[bold green]Validation Passed![/bold green] Output strictly follows the 5-part Strategic Memo format.")

if __name__ == "__main__":
    asyncio.run(test_reasoning())
