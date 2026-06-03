import re
from typing import List

class ChallengeQuestion:
    def __init__(self, assumption: str, question: str):
        self.assumption = assumption
        self.question = question
        
    def to_prompt_text(self) -> str:
        return f"Challenge the founder's assumption about {self.assumption}: {self.question}"

def detect_unchallenged_assumptions(user_message: str, startup_context: dict) -> List[ChallengeQuestion]:
    msg = user_message.lower()
    stage = startup_context.get("stage", "").lower()
    target = startup_context.get("target", "").lower()
    
    challenges = []
    
    # 1. Stage assumptions
    if "pre-revenue" in stage or "seed" in stage:
        if any(word in msg for word in ["ads", "marketing spend", "cac", "scale"]):
            challenges.append(ChallengeQuestion(
                "paid acquisition at seed stage",
                "Are you trying to scale paid acquisition before finding organic product-market fit?"
            ))
            
    # 2. Indian market assumptions
    if "tier 2" in target or "tier 3" in target or "bharat" in target:
        if any(word in msg for word in ["subscription", "saas", "premium", "influencer"]):
            challenges.append(ChallengeQuestion(
                "Tier 2/3 willingness to pay / influence",
                "Have you validated that the parent (the actual buyer) will pay for this, and do they trust this influencer?"
            ))
            
    if any(word in msg for word in ["price", "rs", "₹", "pricing"]):
        challenges.append(ChallengeQuestion(
            "pricing alignment",
            "Is this pricing aligned with the Household Price Index (HPI) for your specific target segment?"
        ))
        
    # 3. Competitive assumptions
    if any(word in msg for word in ["first mover", "no competition", "unique", "stealth"]):
        challenges.append(ChallengeQuestion(
            "competition",
            "Have you checked if someone already tried this in India? What stops Reliance or Tata from entering this space?"
        ))

    return challenges[:2]
