import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel
from src.core.rag.retriever import RetrievalPackage
from src.knowledge.embedder import embedder

class RankedChunk(BaseModel):
    rank: int
    score: float
    reasoning: str
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    collection: str

class HeuristicReranker:
    def __init__(self):
        self.w_relevance = 0.40
        self.w_quality = 0.25
        self.w_recency = 0.15
        self.w_indian = 0.20
        
        self.quality_map = {
            "founders_mindsets": 1.0,
            "market_data_reports": 0.9,
            "campaign_case_studies": 0.9,
            "cmo_profiles": 0.8,
            "books_annotations": 0.8,
            "consumer_psychology": 0.7,
            "startup_context": 0.7,
            "social_intelligence": 0.6
        }

    def _cosine_similarity(self, v1: list, v2: list) -> float:
        a = np.array(v1)
        b = np.array(v2)
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _score_recency(self, meta: dict) -> float:
        year_str = meta.get("year", "")
        if not year_str:
            return 0.5
        try:
            year = int(str(year_str)[:4])
            if year >= 2024: return 1.0
            if year == 2023: return 0.7
            if year >= 2020: return 0.4
            return 0.2
        except:
            return 0.5

    def rerank(self, retrieval_package: RetrievalPackage, original_query: str) -> List[RankedChunk]:
        raw_chunks = retrieval_package.raw_chunks
        if not raw_chunks:
            return []

        # Step 1 - Deduplication (similarity > 0.85)
        deduped = []
        for chunk in raw_chunks:
            is_dup = False
            for j, d_chunk in enumerate(deduped):
                sim = self._cosine_similarity(chunk["vector"], d_chunk["vector"])
                if sim > 0.85:
                    is_dup = True
                    # Keep chunk with richer metadata
                    if len(chunk["metadata"]) > len(d_chunk["metadata"]):
                        deduped[j] = chunk
                    break
            if not is_dup:
                deduped.append(chunk)

        # Step 2 - Embed original query for relevance scoring
        query_vector = embedder.embed(original_query)

        scored_chunks = []
        for chunk in deduped:
            # Semantic relevance
            sim = self._cosine_similarity(query_vector, chunk["vector"])
            rel_score = max(0.0, min(1.0, sim))
            
            # Quality score
            qual_score = self.quality_map.get(chunk["collection"], 0.6)
            
            # Recency
            rec_score = self._score_recency(chunk["metadata"])
            
            # Indian market
            ind_applicable = chunk["metadata"].get("indian_market_applicable", False)
            if isinstance(ind_applicable, str):
                ind_applicable = ind_applicable.lower() == "true"
            ind_score = 1.0 if ind_applicable else 0.0
            
            final_score = (
                self.w_relevance * rel_score +
                self.w_quality * qual_score +
                self.w_recency * rec_score +
                self.w_indian * ind_score
            )
            
            reasoning = f"Rel:{rel_score:.2f} Qual:{qual_score:.2f} Rec:{rec_score:.2f} Ind:{ind_score:.2f}"
            
            scored_chunks.append({
                "chunk": chunk,
                "score": final_score,
                "reasoning": reasoning
            })

        # Sort by final score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)

        # Step 3 - Final selection
        final_selection = []
        source_counts = {}
        has_market_data = False
        
        # Check if we have any market data available
        market_data_available = any(c["chunk"]["collection"] == "market_data_reports" for c in scored_chunks)

        for item in scored_chunks:
            if len(final_selection) >= 8:
                break
                
            chunk = item["chunk"]
            source_id = chunk["metadata"].get("source", "unknown")
            collection = chunk["collection"]
            
            # Prevent single source domination (max 3 chunks per source_id)
            if source_counts.get(source_id, 0) >= 3:
                continue
                
            # If we are at the last slot and haven't included market data yet, but it's available
            if len(final_selection) >= 5 and market_data_available and not has_market_data:
                if collection != "market_data_reports":
                    # Only force it at the very last slot if still missing
                    if len(final_selection) == 7:
                        continue
            
            final_selection.append(item)
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            if collection == "market_data_reports":
                has_market_data = True

        # Convert to RankedChunk Pydantic model
        ranked_results = []
        for rank, item in enumerate(final_selection, 1):
            chunk = item["chunk"]
            ranked_results.append(RankedChunk(
                rank=rank,
                score=item["score"],
                reasoning=item["reasoning"],
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                metadata=chunk["metadata"],
                collection=chunk["collection"]
            ))

        return ranked_results

reranker = HeuristicReranker()
