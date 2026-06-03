import re
from src.memory.context_manager import context_manager
from src.utils.logger import logger

class DecisionTracker:
    def extract_and_log_decision(self, user_question: str, agent_response: str) -> int:
        """Extracts 'THE MOVE' section and logs it as a pending decision."""
        # Look for THE MOVE section, up until THE TRAP or end of string
        move_match = re.search(r'\*\*THE MOVE\*\*(.*?)(?:\*\*THE TRAP|$)', agent_response, re.IGNORECASE | re.DOTALL)
        if not move_match:
            move_match = re.search(r'THE MOVE\n(.*?)(?:THE TRAP|$)', agent_response, re.IGNORECASE | re.DOTALL)
            
        if move_match:
            recommendation = move_match.group(1).strip()
            # Only log if it found a substantial recommendation
            if len(recommendation) > 20:
                logger.info("Auto-extracted decision from response.")
                return context_manager.log_decision(question=user_question, recommendation=recommendation)
        
        return -1

    def log_outcome(self, decision_id: int, outcome_status: str, notes: str):
        """Logs outcome (worked/failed/partial) in decisions_log."""
        full_outcome = f"{outcome_status.upper()}: {notes}"
        context_manager.update_decision_outcome(decision_id, full_outcome)
        logger.info(f"Logged outcome for decision {decision_id}: {outcome_status}")

decision_tracker = DecisionTracker()
