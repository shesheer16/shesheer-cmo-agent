import asyncio
from typing import Dict, Any, List
from src.core.rag.rag_pipeline import rag_pipeline
from src.core.reasoning_engine import reasoning_engine
from src.utils.logger import logger

class ShesheerCMOAgent:
    def __init__(self, startup_context: Dict[str, Any] = None):
        self.startup_context = startup_context or {}
        self.conversation_history: List[str] = []

    async def ask(self, query: str) -> str:
        logger.info(f"Agent received query: {query}")
        # Step 1: Retrieve knowledge context using RAG
        context_package = await rag_pipeline.process(
            user_query=query,
            startup_context=self.startup_context,
            conversation_history=self.conversation_history
        )
        
        # Step 2: Generate advice using reasoning engine
        memo = await reasoning_engine.generate_advice(
            query=query,
            context_package=context_package,
            startup_context=self.startup_context
        )
        
        # Update history
        self.conversation_history.append(f"Founder: {query}")
        self.conversation_history.append(f"CMO: {memo}")
        
        # Keep history bounded
        if len(self.conversation_history) > 6:
            self.conversation_history = self.conversation_history[-6:]
            
        logger.info(f"Agent generated response.")
        return memo

agent = ShesheerCMOAgent()
