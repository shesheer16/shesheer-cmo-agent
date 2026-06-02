import os
from pathlib import Path

PROMPTS_DIR = Path("data/prompts")
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "indian_cmo_persona.txt"

def get_startup_context_text(context: dict) -> str:
    if not context:
        return "No startup context provided."
        
    return f"""Current Domain: {context.get('domain', 'Not specified')}
Product Stage: {context.get('stage', 'Not specified')}
Target Market: {context.get('target_audience', context.get('target_segment', context.get('target', 'Not specified')))}
Current Metrics: {context.get('metrics_summary', context.get('metrics', 'Not specified'))}
Recent Decisions: {context.get('last_3_decisions', context.get('last_decision', 'Not specified'))}
Active Challenge: {context.get('current_challenge', context.get('challenge', 'Not specified'))}"""

def build_system_prompt(startup_context: dict) -> str:
    try:
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            base_prompt = f.read()
    except FileNotFoundError:
        # Fallback if file is missing (should not happen in prod)
        base_prompt = "[STARTUP_CONTEXT_PLACEHOLDER]"
        
    context_str = get_startup_context_text(startup_context)
    
    # Inject context
    final_prompt = base_prompt.replace("[STARTUP_CONTEXT_PLACEHOLDER]", context_str)
    
    return final_prompt
