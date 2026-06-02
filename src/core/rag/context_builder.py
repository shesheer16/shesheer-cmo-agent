from typing import List, Dict, Any
from pydantic import BaseModel
from src.core.rag.reranker import RankedChunk
from src.utils.logger import logger

class ContextPackage(BaseModel):
    formatted_context: str
    total_tokens: int
    chunks_included: int

class ContextBuilder:
    def __init__(self):
        self.MAX_TOKENS = 80000
        self.CHARS_PER_TOKEN = 4

    def build_context(self, ranked_chunks: List[RankedChunk], startup_context: Dict[str, Any], conversation_history: List[str]) -> ContextPackage:
        # Sort chunks by rank (1 is best) to ensure we drop lower-ranked ones if we exceed tokens
        sorted_chunks = sorted(ranked_chunks, key=lambda x: x.rank)
        
        # Build pieces incrementally to track tokens
        startup_str = self._format_startup_context(startup_context)
        conv_str = self._format_conversation_history(conversation_history)
        
        base_tokens = (len(startup_str) + len(conv_str)) // self.CHARS_PER_TOKEN
        
        knowledge_str_parts = ["--- RETRIEVED KNOWLEDGE ---\n"]
        current_tokens = base_tokens + (len(knowledge_str_parts[0]) // self.CHARS_PER_TOKEN)
        chunks_included = 0
        
        for i, chunk in enumerate(sorted_chunks):
            meta = chunk.metadata
            person = meta.get("person", "Unknown")
            source_file = meta.get("url", meta.get("filename", "Unknown Source"))
            year = meta.get("year", "Unknown Year")
            topic = meta.get("topic", "General")
            
            # Applicability string
            app_segments = []
            if meta.get("applicable_segment"):
                app_segments.append(str(meta.get("applicable_segment")))
            if meta.get("market_phase"):
                app_segments.append(str(meta.get("market_phase")))
            applicability = ", ".join(app_segments) if app_segments else "General"
            
            chunk_str = f"[{i+1}] SOURCE: {person} / {source_file} ({year})\n"
            chunk_str += f"    TOPIC: {topic}\n"
            chunk_str += f"    INSIGHT: {chunk.text}\n"
            chunk_str += f"    APPLICABILITY: {applicability}\n\n"
            
            chunk_tokens = len(chunk_str) // self.CHARS_PER_TOKEN
            
            if current_tokens + chunk_tokens > self.MAX_TOKENS:
                logger.warning(f"Context exceeds {self.MAX_TOKENS} tokens. Truncating chunks from rank {chunk.rank} onwards.")
                break
                
            knowledge_str_parts.append(chunk_str)
            current_tokens += chunk_tokens
            chunks_included += 1

        final_knowledge_str = "".join(knowledge_str_parts)
        
        formatted_context = f"{final_knowledge_str}{startup_str}{conv_str}"
        
        logger.info(f"Built context package: {chunks_included}/{len(ranked_chunks)} chunks, {current_tokens} estimated tokens.")
        
        return ContextPackage(
            formatted_context=formatted_context,
            total_tokens=current_tokens,
            chunks_included=chunks_included
        )
        
    def _format_startup_context(self, startup_context: Dict[str, Any]) -> str:
        if not startup_context:
            return "--- YOUR STARTUP CONTEXT ---\n(No startup context provided)\n\n"
            
        domain = startup_context.get("domain", startup_context.get("sector", "Unknown Domain"))
        stage = startup_context.get("stage", "Unknown Stage")
        target = startup_context.get("target", startup_context.get("users", "Unknown Target"))
        last_decision = startup_context.get("last_decision", "None")
        
        context_str = "--- YOUR STARTUP CONTEXT ---\n"
        context_str += f"Domain: {domain}\n"
        context_str += f"Stage: {stage}\n"
        context_str += f"Target: {target}\n"
        context_str += f"Last decision: {last_decision}\n\n"
        
        return context_str
        
    def _format_conversation_history(self, history: List[str]) -> str:
        if not history:
            return "--- CONVERSATION CONTEXT ---\n(No prior history)\n\n"
            
        history_str = "--- CONVERSATION CONTEXT ---\n"
        for entry in history[-3:]: # Ensure we only grab the last 3 if more are passed
            history_str += f"- {entry}\n"
            
        return history_str + "\n"

context_builder = ContextBuilder()
