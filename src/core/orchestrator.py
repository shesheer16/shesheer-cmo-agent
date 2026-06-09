import time
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from src.core.rag.rag_pipeline import rag_pipeline
from src.core.reasoning_engine import reasoning_engine
from src.core.system_prompt import build_system_prompt
from src.core.response_formatter import response_formatter
from src.core.challenger import detect_unchallenged_assumptions
from src.core.decision_tracker import decision_tracker

# We'll assume USD to INR conversion rate
USD_TO_INR = 83.50

class AgentResponse(BaseModel):
    response_text: str
    sources_used: List[str]
    tokens_used: int
    cost_inr: float
    model_used: str
    retrieval_time_ms: int
    total_time_ms: int

from src.memory.context_manager import context_manager, ConversationData


class CMOAgent:
    
    async def respond(self, user_message: str, output_format: str = "telegram") -> AgentResponse:
        total_start = time.time()
        
        # 1. Load context and history from memory layer
        startup_context = context_manager.get_context()
        history = context_manager.get_recent_conversations(n=5)
        
        # 2. Build system prompt & inject challenges
        system_prompt = build_system_prompt(startup_context)
        
        challenges = detect_unchallenged_assumptions(user_message, startup_context)
        if challenges:
            challenge_texts = "\n".join([c.to_prompt_text() for c in challenges])
            system_prompt += f"\n\n[CHALLENGER MODE ACTIVATED]\nIntegrate these challenges into your reasoning if relevant:\n{challenge_texts}"
            
        # 3. Retrieve context via RAG Pipeline
        rag_start = time.time()
        context_package = await rag_pipeline.process(
            user_query=user_message,
            startup_context=startup_context,
            conversation_history=history
        )
        retrieval_time_ms = int((time.time() - rag_start) * 1000)
        
        # Determine model
        model = "gemini-2.5-flash"
        
        # 4. Call Gemini API
        raw_response = await reasoning_engine.generate_advice(
            query=user_message,
            context_package=context_package,
            startup_context=startup_context
        )
        
        # 5. Format response based on requested output type
        if output_format == "telegram":
            formatted_text = response_formatter.format_for_telegram(raw_response)
        elif output_format == "voice":
            formatted_text = response_formatter.format_for_voice(raw_response)
        elif output_format == "streamlit":
            formatted_text = response_formatter.format_for_streamlit(raw_response)
        else:
            formatted_text = raw_response
            
        # Extract and log decision automatically
        decision_tracker.extract_and_log_decision(user_message, raw_response)
        
        # We save this later after we extract sources and tokens.
        
        # Extract sources used
        sources_used = context_package.sources
        
        # Extract cost and tokens from Gemini estimation (Mocked for free tier)
        est_input_tokens = len(system_prompt + context_package.formatted_context + user_message) // 4
        est_output_tokens = len(raw_response) // 4
        total_tokens = est_input_tokens + est_output_tokens
        
        # Gemini Free Tier has 0 cost, but if paid it's ~ $0.075 per 1M input / $0.30 per 1M output
        usd_cost = (est_input_tokens / 1_000_000 * 0.075) + (est_output_tokens / 1_000_000 * 0.30)
        cost_inr = usd_cost * USD_TO_INR
        
        # 6. Save to memory
        conv_data = ConversationData(
            user_message=user_message,
            agent_response=raw_response,
            sources=sources_used,
            tokens_used=total_tokens,
            cost_inr=cost_inr,
            model=model,
            conv_type="strategy"
        )
        conv_id = context_manager.save_conversation(conv_data)
        context_manager.update_cost_tracker(tokens=total_tokens, cost=cost_inr, model=model, conversation_id=conv_id)
        
        total_time_ms = int((time.time() - total_start) * 1000)
        
        return AgentResponse(
            response_text=formatted_text,
            sources_used=sources_used,
            tokens_used=total_tokens,
            cost_inr=cost_inr,
            model_used=model,
            retrieval_time_ms=retrieval_time_ms,
            total_time_ms=total_time_ms
        )

    def test_respond(self, question: str):
        """Prints full debug including which chunks were retrieved and why."""
        print(f"\n{'='*60}\nDEBUG ORCHESTRATOR TEST\n{'='*60}")
        print(f"Question: {question}\n")
        
        # Run async logic synchronously
        start = time.time()
        
        # Step-by-step debug logic mirroring respond
        startup_context = context_manager.get_context()
        print(f"1. Loaded Startup Context: {startup_context}")
        
        history = context_manager.get_recent_conversations(n=5)
        print(f"2. Loaded History: {len(history)} turns")
        
        context_package = asyncio.run(rag_pipeline.process(question, startup_context, history))
        
        print("\n3. RAG Retrieval Details:")
        print(f"   - Retrieved {context_package.chunks_included} chunks")
        for i, source in enumerate(context_package.sources):
            print(f"     [{i+1}] Source: {source}")
            
        print("\n4. Generating Response (Calling Gemini)...")
        response = asyncio.run(self.respond(question, output_format="telegram"))
        
        print(f"\n5. Execution Stats:")
        print(f"   - Model: {response.model_used}")
        print(f"   - Tokens: ~{response.tokens_used}")
        print(f"   - Cost: ₹{response.cost_inr:.4f}")
        print(f"   - Retrieval Time: {response.retrieval_time_ms}ms")
        print(f"   - Total Time: {response.total_time_ms}ms")
        
        print("\n6. Final Output Preview (First 500 chars):")
        print("-" * 40)
        print(response.response_text[:500] + "...")
        print("-" * 40)

cmo_agent = CMOAgent()
