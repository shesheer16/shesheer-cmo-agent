import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.memory.database import SessionLocal
from src.memory.models import StartupContext, Conversation, DecisionsLog, PivotsLog, CostTracker
from src.utils.logger import logger

class ConversationData:
    def __init__(self, user_message: str, agent_response: str, sources: List[str] = None, 
                 tokens_used: int = 0, cost_inr: float = 0.0, model: str = "unknown", 
                 conv_type: str = "strategy"):
        self.user_message = user_message
        self.agent_response = agent_response
        self.sources = sources or []
        self.tokens_used = tokens_used
        self.cost_inr = cost_inr
        self.model = model
        self.conv_type = conv_type

class ContextManager:
    def __init__(self):
        pass
        
    def _get_session(self) -> Session:
        return SessionLocal()

    def update_context(self, field: str, value: Any) -> bool:
        """Saves a context field to the startup_context table."""
        with self._get_session() as db:
            context_entry = db.query(StartupContext).filter(StartupContext.field_name == field).first()
            if context_entry:
                context_entry.field_value = str(value)
            else:
                context_entry = StartupContext(field_name=field, field_value=str(value))
                db.add(context_entry)
            db.commit()
            return True

    def get_context(self) -> Dict[str, Any]:
        """Returns dict of all current context fields."""
        with self._get_session() as db:
            context_entries = db.query(StartupContext).all()
            return {entry.field_name: entry.field_value for entry in context_entries}

    def get_context_summary(self) -> str:
        """Returns condensed 200-word string for prompt."""
        ctx = self.get_context()
        if not ctx:
            return "No startup context provided yet."
            
        summary_parts = []
        for key in ["domain", "product_stage", "target_segment", "current_mrr", "team_size", "burn_rate", "last_pivot", "active_challenge", "key_metrics"]:
            if key in ctx:
                summary_parts.append(f"{key.replace('_', ' ').title()}: {ctx[key]}")
        
        # fallback for any other fields
        for k, v in ctx.items():
            if k not in ["domain", "product_stage", "target_segment", "current_mrr", "team_size", "burn_rate", "last_pivot", "active_challenge", "key_metrics"]:
                summary_parts.append(f"{k.replace('_', ' ').title()}: {v}")
                
        return "\n".join(summary_parts)

    def save_conversation(self, conv_data: ConversationData) -> int:
        """Saves a conversation turn to DB."""
        with self._get_session() as db:
            conv = Conversation(
                user_message=conv_data.user_message,
                agent_response=conv_data.agent_response,
                sources_used=conv_data.sources,
                tokens_used=conv_data.tokens_used,
                cost_inr=conv_data.cost_inr,
                model_used=conv_data.model,
                conversation_type=conv_data.conv_type,
                compression_status=False
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            return conv.id

    def update_cost_tracker(self, tokens: int, cost: float, model: str = "unknown", conversation_id: int = None):
        with self._get_session() as db:
            tracker = CostTracker(
                model=model,
                input_tokens=0, # Simplifying as total tokens
                output_tokens=tokens,
                cost_inr=cost,
                conversation_id=conversation_id
            )
            db.add(tracker)
            db.commit()

    def get_recent_conversations(self, n: int = 5) -> List[str]:
        """Returns last N relevant conversations."""
        with self._get_session() as db:
            convs = db.query(Conversation).order_by(Conversation.timestamp.desc()).limit(n).all()
            history = []
            for c in reversed(convs): # Chronological order
                history.append(f"Founder: {c.user_message}\nCMO: {c.agent_response}")
            return history

    def get_conversation_summary(self, days: int = 30) -> str:
        """
        Compressed monthly summary.
        For conversations > 30 days old, return 1-line summary.
        For recent < 30 days, return full text.
        Compress on-the-fly (don't persist).
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        with self._get_session() as db:
            convs = db.query(Conversation).order_by(Conversation.timestamp.asc()).all()
            
            parts = []
            for c in convs:
                # Need to handle timezone-aware or naive datetimes correctly
                # We'll just assume timestamp is timezone-aware from sqlite or convert appropriately
                if c.timestamp.replace(tzinfo=timezone.utc) < cutoff_date:
                    # Compress on the fly
                    # Rough 1-line summary: First 50 chars of user message -> First 50 chars of response
                    u_short = c.user_message[:50] + "..." if len(c.user_message) > 50 else c.user_message
                    r_short = c.agent_response[:50] + "..." if len(c.agent_response) > 50 else c.agent_response
                    parts.append(f"[{c.timestamp.strftime('%Y-%m-%d')}] (Archived) Founder asked about {u_short}. CMO replied: {r_short}")
                else:
                    parts.append(f"[{c.timestamp.strftime('%Y-%m-%d')}] Founder: {c.user_message}\nCMO: {c.agent_response}")
                    
            return "\n\n".join(parts)

    def log_decision(self, question: str, recommendation: str, decision_taken: str = None) -> int:
        with self._get_session() as db:
            dec = DecisionsLog(
                decision_question=question,
                recommendation_given=recommendation,
                decision_taken=decision_taken
            )
            db.add(dec)
            db.commit()
            db.refresh(dec)
            return dec.id

    def update_decision_outcome(self, decision_id: int, outcome: str):
        with self._get_session() as db:
            dec = db.query(DecisionsLog).filter(DecisionsLog.id == decision_id).first()
            if dec:
                dec.outcome = outcome
                db.commit()

    def get_pending_decisions(self) -> List[Dict]:
        """Returns decisions without outcomes."""
        with self._get_session() as db:
            decs = db.query(DecisionsLog).filter(DecisionsLog.outcome == None).all()
            return [{"id": d.id, "question": d.decision_question, "recommendation": d.recommendation_given} for d in decs]

context_manager = ContextManager()
