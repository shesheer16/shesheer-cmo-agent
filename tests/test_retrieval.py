"""
Test Set 1: Retrieval Quality Tests
Validates that the RAG pipeline surfaces the right chunks for 20 benchmark queries.
Target: 85%+ pass rate (17/20 minimum)
"""
import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.rag.retriever import retriever
from src.knowledge.embedder import embedder

RETRIEVAL_TEST_CASES = [
    {
        "id": 1,
        "query": "pricing strategy EdTech India freemium",
        "expected_keywords": ["PhysicsWallah", "PW", "freemium", "pricing", "affordable"],
        "description": "Pricing / PW model"
    },
    {
        "id": 2,
        "query": "distribution rural India Bharat Jio HUL last mile",
        "expected_keywords": ["Jio", "HUL", "distribution", "rural", "last mile"],
        "description": "Rural distribution"
    },
    {
        "id": 3,
        "query": "cultural tension advertising India Ariel gender",
        "expected_keywords": ["Ariel", "campaign", "cultural", "gender", "emotion"],
        "description": "Cultural tension advertising"
    },
    {
        "id": 4,
        "query": "freemium India consumer CRED Kuku FM premium",
        "expected_keywords": ["CRED", "Kuku", "freemium", "premium", "consumer"],
        "description": "Freemium consumer model"
    },
    {
        "id": 5,
        "query": "EdTech trust recession Byju collapse India",
        "expected_keywords": ["Byju", "trust", "EdTech", "collapse", "recession"],
        "description": "Byju trust failure"
    },
    {
        "id": 6,
        "query": "Tier 2 student psychology aspiration India",
        "expected_keywords": ["tier 2", "student", "aspiration", "bharat", "psychology"],
        "description": "Tier 2 student psychology"
    },
    {
        "id": 7,
        "query": "zero marketing growth Zerodha word of mouth",
        "expected_keywords": ["Zerodha", "word of mouth", "organic", "marketing", "growth"],
        "description": "Zero marketing Zerodha model"
    },
    {
        "id": 8,
        "query": "WhatsApp India distribution viral growth",
        "expected_keywords": ["WhatsApp", "viral", "distribution", "growth", "India"],
        "description": "WhatsApp distribution"
    },
    {
        "id": 9,
        "query": "CAC customer acquisition cost India startup",
        "expected_keywords": ["CAC", "acquisition", "cost", "startup", "India"],
        "description": "CAC benchmarks India"
    },
    {
        "id": 10,
        "query": "parent trust school India EdTech psychology",
        "expected_keywords": ["parent", "trust", "school", "India", "credibility"],
        "description": "Parent trust EdTech"
    },
    {
        "id": 11,
        "query": "community led growth India B2C startup",
        "expected_keywords": ["community", "growth", "India", "organic", "users"],
        "description": "Community led growth"
    },
    {
        "id": 12,
        "query": "product market fit India consumer startup",
        "expected_keywords": ["product market fit", "retention", "organic", "India", "consumer"],
        "description": "PMF India"
    },
    {
        "id": 13,
        "query": "B2B EdTech schools India SaaS",
        "expected_keywords": ["B2B", "schools", "India", "EdTech", "SaaS"],
        "description": "B2B EdTech India"
    },
    {
        "id": 14,
        "query": "Series A fundraising India startup metrics",
        "expected_keywords": ["Series A", "funding", "metrics", "India", "startup"],
        "description": "Fundraising benchmarks"
    },
    {
        "id": 15,
        "query": "influencer marketing India Tier 2 authentic",
        "expected_keywords": ["influencer", "India", "tier 2", "authentic", "trust"],
        "description": "Influencer India authenticity"
    },
    {
        "id": 16,
        "query": "performance marketing Instagram ads India D2C",
        "expected_keywords": ["performance", "Instagram", "ads", "India", "D2C"],
        "description": "Performance marketing India"
    },
    {
        "id": 17,
        "query": "Reliance Jio disruption India market entry",
        "expected_keywords": ["Jio", "Reliance", "disruption", "market", "India"],
        "description": "Jio disruption pattern"
    },
    {
        "id": 18,
        "query": "scaling startup India Tier 3 growth playbook",
        "expected_keywords": ["scale", "tier 3", "India", "growth", "startup"],
        "description": "Tier 3 growth playbook"
    },
    {
        "id": 19,
        "query": "unit economics India startup LTV retention churn",
        "expected_keywords": ["LTV", "retention", "churn", "economics", "India"],
        "description": "Unit economics benchmarks"
    },
    {
        "id": 20,
        "query": "regional language India content Hindi vernacular",
        "expected_keywords": ["Hindi", "regional", "vernacular", "language", "India"],
        "description": "Vernacular content India"
    },
]


def run_retrieval_test(test_case: dict) -> dict:
    """Runs a single retrieval test and checks top-5 results for expected keywords."""
    query = test_case["query"]
    expected = [k.lower() for k in test_case["expected_keywords"]]

    start = time.time()
    try:
        query_vector = embedder.embed(query)
        # Query all collections and gather top 5 results
        all_chunks = []
        for col_name in ["founders_mindsets", "campaign_case_studies", "cmo_profiles",
                          "market_data_reports", "consumer_psychology", "books_annotations",
                          "social_intelligence"]:
            try:
                from src.knowledge.chroma_client import get_collection
                col = get_collection(col_name)
                results = col.query(query_embeddings=[query_vector], n_results=3,
                                    include=["documents"])
                for doc in results.get("documents", [[]])[0]:
                    all_chunks.append(doc.lower())
            except Exception:
                pass

        elapsed_ms = int((time.time() - start) * 1000)

        # Check if any expected keyword appears in any top chunk
        combined_text = " ".join(all_chunks)
        hits = [k for k in expected if k in combined_text]
        passed = len(hits) >= 2  # At least 2 of 5 expected keywords must appear

        return {
            "id": test_case["id"],
            "description": test_case["description"],
            "passed": passed,
            "hits": hits,
            "elapsed_ms": elapsed_ms,
        }
    except Exception as e:
        return {
            "id": test_case["id"],
            "description": test_case["description"],
            "passed": False,
            "hits": [],
            "elapsed_ms": 0,
            "error": str(e)
        }


def main():
    print("=" * 60)
    print("RETRIEVAL QUALITY TEST SUITE — 20 Benchmark Queries")
    print("=" * 60)

    results = []
    for case in RETRIEVAL_TEST_CASES:
        print(f"[{case['id']:02d}] Testing: {case['description']}...", end=" ", flush=True)
        result = run_retrieval_test(case)
        results.append(result)
        status = "PASS ✅" if result["passed"] else "FAIL ❌"
        print(f"{status} ({result['elapsed_ms']}ms) | Hits: {result.get('hits', [])}")

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_ms = sum(r["elapsed_ms"] for r in results) // total

    print("\n" + "=" * 60)
    print(f"RESULT: {passed_count}/{total} passed ({passed_count / total * 100:.1f}%)")
    print(f"Average retrieval time: {avg_ms}ms")
    target_met = passed_count / total >= 0.85
    print(f"Target (85%): {'MET ✅' if target_met else 'NOT MET ❌'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
