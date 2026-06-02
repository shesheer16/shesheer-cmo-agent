import json
from google import genai
from pydantic import BaseModel, Field
from src.config import settings
from src.utils.logger import logger
from src.core.rag.context_builder import ContextPackage
from src.core.system_prompt import build_system_prompt

class StrategicMemo(BaseModel):
    situation_analysis: str = Field(description="Max 3 sentences. Be direct. No fluff.")
    indian_market_precedent: str = Field(description="Specific company + specific situation + specific outcome.")
    the_move: str = Field(description="Your specific, directional recommendation. One move. With clear reasoning.")
    the_trap_to_avoid: str = Field(description="The obvious wrong move and why it's wrong in India.")
    the_question_you_havent_asked: str = Field(description="The assumption in the founder's thinking that needs to be stress-tested.")

class ReasoningEngine:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.default_model

    async def generate_advice(self, query: str, context_package: ContextPackage, startup_context: dict) -> str:
        # Build the system instruction from the dedicated manager
        system_instruction = build_system_prompt(startup_context)
        
        prompt = f"""
Founder's Query: {query}

Retrieved Context from Knowledge Base:
{context_package.formatted_context}

Analyze the situation and output your strategic memo.
"""
        logger.info("Executing Reasoning Engine (Gemini 2.5 Flash)...")
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=StrategicMemo,
                    temperature=0.3
                )
            )
            
            data = json.loads(response.text)
            
            # Format the output into the final markdown memo
            memo = f"**SITUATION ANALYSIS**\n{data.get('situation_analysis', '')}\n\n"
            memo += f"**INDIAN MARKET PRECEDENT**\n{data.get('indian_market_precedent', '')}\n\n"
            memo += f"**THE MOVE**\n{data.get('the_move', '')}\n\n"
            memo += f"**THE TRAP TO AVOID**\n{data.get('the_trap_to_avoid', '')}\n\n"
            memo += f"**THE QUESTION YOU HAVEN'T ASKED**\n{data.get('the_question_you_havent_asked', '')}\n"
            
            return memo
            
        except Exception as e:
            logger.error(f"Reasoning engine failed: {e}")
            return f"Error executing reasoning engine: {e}"

reasoning_engine = ReasoningEngine()
