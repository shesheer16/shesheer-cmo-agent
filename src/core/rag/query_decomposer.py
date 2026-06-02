import time
import re
from typing import List
from src.utils.logger import logger

class QueryDecomposer:
    def __init__(self):
        self.target_keywords = [
            "pricing", "distribution", "trust", "growth", 
            "brand", "psychology", "marketing", "sales", "roi", "cac"
        ]

    def classify_query_complexity(self, query: str) -> str:
        # Simple heuristic classification
        words = query.split()
        if len(words) < 4:
            return "SIMPLE"
        if any(w.lower() in ["i", "my", "we", "our"] for w in words):
            return "PERSONAL"
        return "COMPLEX"

    def fast_decompose(self, query: str, context: str = "") -> List[str]:
        # Fast decompose returns just 2 queries
        return [query, f"{query} India market"]

    def decompose(self, query: str, context: str = "") -> List[str]:
        category = self.classify_query_complexity(query)
        if category == "SIMPLE":
            sub_queries = self.fast_decompose(query, context)
        elif category == "PERSONAL":
            sub_queries = self._keyword_decompose(query, count=3)
        else:
            sub_queries = self._keyword_decompose(query, count=5)
            
        logger.info(f"Query decomposition ({category}) generated {len(sub_queries)} sub-queries.")
        logger.info("Decomposition cost: $0.00 (Local Keyword-based)")
        return sub_queries

    def _keyword_decompose(self, query: str, count: int) -> List[str]:
        start_time = time.time()
        
        # 1. Extract keywords
        query_lower = query.lower()
        found_keywords = [kw for kw in self.target_keywords if kw in query_lower]
        
        # Try to find a company name (capitalized words that aren't at the start, or just assume the first capitalized word is the company if no others)
        words = query.split()
        company = ""
        capitalized_words = [w for w in words if w and w[0].isupper()]
        if capitalized_words:
            # Just take the first capitalized word as a heuristic for company
            company = capitalized_words[0].strip(".,?!'")
            
        if not found_keywords:
            # If no specific keywords matched, just split into words > 4 chars
            found_keywords = [w for w in words if len(w) > 4][:2]
            if not found_keywords:
                found_keywords = ["strategy"]

        keyword = found_keywords[0]
        
        # 2. Generate sub-queries
        sub_queries = [query] # Always include the original query
        
        if company:
            sub_queries.append(f"{company} {keyword}")
            sub_queries.append(f"{company} what failed or succeeded")
            
        sub_queries.append(f"{keyword} India market")
        sub_queries.append(f"{keyword} Tier2 Tier3")
        
        # Fill remaining slots if we don't have enough
        if len(sub_queries) < count:
            if len(found_keywords) > 1:
                sub_queries.append(f"{found_keywords[1]} psychology India")
            else:
                sub_queries.append(f"Indian consumer trust {keyword}")
                
        # Deduplicate and trim to exactly 'count'
        unique_queries = []
        for q in sub_queries:
            if q not in unique_queries:
                unique_queries.append(q)
                
        final_queries = unique_queries[:count]
        
        elapsed = time.time() - start_time
        logger.debug(f"Keyword decomposition took {elapsed:.4f}s")
        
        return final_queries

    # For compatibility with rag_pipeline.py which calls this explicitly
    def _do_decompose(self, query: str, context: str, count: int, category: str) -> List[str]:
        return self._keyword_decompose(query, count)

query_decomposer = QueryDecomposer()
