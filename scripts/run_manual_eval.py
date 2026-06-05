"""
scripts/run_manual_eval.py
Runs all 20 EdTech test questions through CMOAgent.respond()
and saves full output to test_results.md for human grading.

Usage:
  uv run python scripts/run_manual_eval.py
"""
import sys
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import CMOAgent

QUESTIONS_FILE = Path("tests/test_questions.json")
RESULTS_FILE = Path("tests/test_results.md")


GRADING_TEMPLATE = """
| Dimension                 | Score (1-5) | Notes |
|---------------------------|-------------|-------|
| Indian Market Specificity |             |       |
| Actionability             |             |       |
| Challenger Mode Quality   |             |       |
| Source Citation Quality   |             |       |
"""


async def run_evaluation():
    questions = json.loads(QUESTIONS_FILE.read_text())
    agent = CMOAgent()

    md_lines = [
        f"# CMO Agent — Manual Evaluation Results\n",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**Questions:** {len(questions)}\n",
        f"**Target:** All dimensions ≥ 4/5\n",
        f"---\n",
    ]

    for q in questions:
        qid = q["id"]
        question = q["q"]
        print(f"\n[{qid:02d}/{len(questions)}] Asking: {question[:70]}...")

        start = time.time()
        try:
            response = await agent.respond(question, output_format="streamlit")
            elapsed = int((time.time() - start) * 1000)

            md_lines.append(f"\n## Question {qid:02d}\n")
            md_lines.append(f"**Q:** {question}\n")
            md_lines.append(f"**Response Time:** {elapsed}ms\n")
            md_lines.append(f"**Sources Used:** {len(response.sources_used)} — {', '.join(response.sources_used[:5]) or 'None'}\n")
            md_lines.append(f"**Tokens:** {response.tokens_used} | **Cost:** ₹{response.cost_inr:.4f}\n")
            md_lines.append(f"\n### Agent Response\n")
            md_lines.append(f"{response.response_text}\n")
            md_lines.append(f"\n### Grading\n{GRADING_TEMPLATE}\n")
            md_lines.append(f"---\n")

            print(f"    ✅ Done ({elapsed}ms) — {len(response.sources_used)} sources")

        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            md_lines.append(f"\n## Question {qid:02d}\n")
            md_lines.append(f"**Q:** {question}\n")
            md_lines.append(f"**ERROR:** {e}\n")
            md_lines.append(f"---\n")
            print(f"    ❌ Error: {e}")

        # Polite pause to avoid 429 rate limits on free tier
        await asyncio.sleep(5)

    RESULTS_FILE.write_text("\n".join(md_lines))
    print(f"\n{'='*60}")
    print(f"All {len(questions)} questions completed.")
    print(f"Results saved to: {RESULTS_FILE}")
    print(f"Now open the file and fill in the grading tables.")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
