import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel
import concurrent.futures
from src.knowledge.embedder import embedder
from src.knowledge.chroma_client import get_collection
from src.utils.logger import logger

class RetrievalPackage(BaseModel):
    sub_questions: List[str]
    raw_chunks: List[Dict[str, Any]]
    collection_sources: List[str]
    total_tokens_estimate: int

class Retriever:
    def __init__(self):
        self.all_collections = [
            "founders_mindsets",
            "campaign_case_studies",
            "cmo_profiles",
            "market_data_reports",
            "consumer_psychology",
            "books_annotations",
            "social_intelligence",
            "startup_context"
        ]

    def _determine_collections(self, question: str) -> List[str]:
        q = question.lower()
        cols = set(["startup_context", "founders_mindsets"]) # Always include base context and founders where our videos are

        if any(w in q for w in ["founder", "ceo", "people", "person", "leader"]):
            cols.update(["cmo_profiles"])
        if any(w in q for w in ["campaign", "brand", "marketing", "ads"]):
            cols.update(["campaign_case_studies", "consumer_psychology"])
        if any(w in q for w in ["data", "market", "report", "growth", "revenue", "cagr"]):
            cols.update(["market_data_reports"])
        if any(w in q for w in ["psychology", "trust", "behavior", "consumer"]):
            cols.update(["consumer_psychology", "campaign_case_studies"])
        if any(w in q for w in ["cmo", "officer", "strategy"]):
            cols.update(["cmo_profiles"])
        
        return list(cols)

    def _build_where_filter(self, startup_context: dict) -> dict:
        where = {}
        filters = []
        
        # We disable strict metadata filtering for now because it causes 0 chunks returned
        # if the ingested sources (like youtube videos) don't have the exact matching metadata keys.
        return None

    def _cosine_similarity(self, v1: list, v2: list) -> float:
        a = np.array(v1)
        b = np.array(v2)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _query_collection(self, col_name: str, vector: list, n_results: int, where_filter: dict) -> List[Dict]:
        results = []
        if not vector:
            return results
        try:
            coll = get_collection(col_name)
            if coll.count() == 0:
                return results
                
            # If where_filter contains fields not present in some collections, Chroma might throw an error.
            try:
                res = coll.query(
                    query_embeddings=[vector],
                    n_results=n_results,
                    where=where_filter,
                    include=["documents", "metadatas", "distances", "embeddings"]
                )
            except Exception as e:
                # Fallback without where filter if schema validation fails for a specific collection
                logger.debug(f"Query with filter failed on {col_name}, retrying without filter: {e}")
                res = coll.query(
                    query_embeddings=[vector],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances", "embeddings"]
                )
                
            if not res or not res.get("ids") or not res["ids"][0]:
                return results
                
            for i in range(len(res["ids"][0])):
                results.append({
                    "chunk_id": res["ids"][0][i],
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "vector": res["embeddings"][0][i],
                    "collection": col_name,
                    "base_distance": res["distances"][0][i]
                })
        except Exception as e:
            logger.debug(f"Retriever error on collection {col_name}: {e}")
        return results

    def retrieve(self, sub_questions: List[str], startup_context: dict = None, n_results_per_q: int = 3) -> RetrievalPackage:
        all_results = []
        collections_queried = set()
        
        # We process sub-queries sequentially for embedding
        embeddings = embedder.embed_batch(sub_questions)
        where_filter = self._build_where_filter(startup_context or {})
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for idx, (query, vector) in enumerate(zip(sub_questions, embeddings)):
                target_cols = self._determine_collections(query)
                for col in target_cols:
                    collections_queried.add(col)
                    futures.append(
                        executor.submit(self._query_collection, col, vector, n_results_per_q, where_filter)
                    )
            
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
                
        # Deduplicate globally
        unique_results = []
        seen_texts = set()
        
        all_results.sort(key=lambda x: x["base_distance"])
        
        for item in all_results:
            if len(unique_results) >= 15: # max_total_chunks
                break
                
            text_hash = hash(item["text"])
            if text_hash in seen_texts:
                continue
                
            is_dup = False
            for u in unique_results:
                if self._cosine_similarity(item["vector"], u["vector"]) > 0.95:
                    is_dup = True
                    break
                    
            if not is_dup:
                seen_texts.add(text_hash)
                unique_results.append(item)
                
        # Estimate tokens (roughly 1 token per 4 chars for text)
        total_tokens = sum(len(r["text"]) // 4 for r in unique_results)
        
        logger.info(f"Retrieved {len(unique_results)} unique chunks from {len(sub_questions)} sub-queries.")
        
        return RetrievalPackage(
            sub_questions=sub_questions,
            raw_chunks=unique_results,
            collection_sources=list(collections_queried),
            total_tokens_estimate=total_tokens
        )

retriever = Retriever()
