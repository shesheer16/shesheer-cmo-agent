import time
import asyncio
from typing import List, Dict, Any
from src.utils.logger import logger
from src.core.rag.query_decomposer import query_decomposer
from src.core.rag.retriever import retriever
from src.core.rag.reranker import reranker
from src.core.rag.context_builder import context_builder, ContextPackage

class RAGPipeline:
    def __init__(self):
        self.last_stats = {}

    async def process(self, user_query: str, startup_context: Dict[str, Any], conversation_history: List[str]) -> ContextPackage:
        logger.info(f"Starting RAG Pipeline for query: {user_query}")
        self.last_stats = {}
        total_start = time.time()

        # Step 1: Classify complexity
        t0 = time.time()
        complexity = query_decomposer.classify_query_complexity(user_query)
        self._record_time("classify", t0)

        # Step 2: Decompose
        t0 = time.time()
        # We modified decompose to handle complexity internally, but following the spec we use it.
        if complexity == "SIMPLE":
            sub_questions = query_decomposer.fast_decompose(user_query, str(startup_context))
        elif complexity == "PERSONAL":
            sub_questions = query_decomposer._do_decompose(user_query, str(startup_context), count=3, category="PERSONAL")
        else:
            sub_questions = query_decomposer._do_decompose(user_query, str(startup_context), count=5, category="COMPLEX")
        self._record_time("decompose", t0)

        # Step 3: Retrieve
        t0 = time.time()
        # Convert threaded/synchronous retrieve to run in executor if we want strict async, 
        # but since retriever uses ThreadPool internally, we can just call it synchronously here
        # or offload to thread. We'll call it directly for now.
        raw_results = retriever.retrieve(sub_questions, startup_context=startup_context, n_results_per_q=3)
        self._record_time("retrieve", t0)

        # Step 4: Rerank
        t0 = time.time()
        ranked_chunks = reranker.rerank(raw_results, user_query)
        self._record_time("rerank", t0)

        # Step 5: Build context
        t0 = time.time()
        context_package = context_builder.build_context(ranked_chunks, startup_context, conversation_history)
        self._record_time("build_context", t0)

        total_elapsed = time.time() - total_start
        self.last_stats["total_time"] = total_elapsed
        logger.info(f"RAG Pipeline completed in {total_elapsed:.2f}s")
        
        return context_package

    def _record_time(self, step_name: str, start_time: float):
        elapsed = time.time() - start_time
        self.last_stats[step_name] = elapsed
        if elapsed > 5.0:
            logger.warning(f"RAG Pipeline Step '{step_name}' took > 5 seconds ({elapsed:.2f}s)")
        else:
            logger.debug(f"Step '{step_name}': {elapsed:.2f}s")

    def get_pipeline_stats(self) -> Dict[str, Any]:
        return self.last_stats

    def test_retrieval(self, query: str):
        """Debug mode showing full pipeline synchronously."""
        print(f"\n{'='*50}\nDEBUG RAG PIPELINE: {query}\n{'='*50}")
        startup_context = {"domain": "Test Domain", "stage": "Test", "target": "Test", "last_decision": "None"}
        
        # Run async process in sync wrapper for debugging
        context_pkg = asyncio.run(self.process(query, startup_context, []))
        
        print(f"\n[STATS]")
        for step, t in self.get_pipeline_stats().items():
            print(f"  {step}: {t:.3f}s")
            
        print(f"\n[RESULTS]")
        print(f"  Tokens: {context_pkg.total_tokens}")
        print(f"  Chunks: {context_pkg.chunks_included}")
        print(f"\n[CONTEXT PACKAGE PREVIEW]")
        print(context_pkg.formatted_context[:1000] + "...\n(truncated)")

rag_pipeline = RAGPipeline()
