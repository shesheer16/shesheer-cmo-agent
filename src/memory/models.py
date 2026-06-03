from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from src.memory.database import Base

class StartupContext(Base):
    __tablename__ = "startup_context"
    
    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, unique=True, index=True, nullable=False)
    field_value = Column(String, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_message = Column(String, nullable=False)
    agent_response = Column(String, nullable=False)
    sources_used = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_inr = Column(Float, default=0.0)
    model_used = Column(String, nullable=True)
    conversation_type = Column(String, nullable=True) # strategy/question/update
    compression_status = Column(Boolean, default=False)
    compressed_summary = Column(String, nullable=True)

class DecisionsLog(Base):
    __tablename__ = "decisions_log"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    decision_question = Column(String, nullable=False)
    recommendation_given = Column(String, nullable=False)
    decision_taken = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    follow_up_date = Column(DateTime(timezone=True), nullable=True)

class PivotsLog(Base):
    __tablename__ = "pivots_log"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    pivot_suggested = Column(String, nullable=False)
    pivot_context = Column(String, nullable=False)
    pivot_taken = Column(Boolean, default=False)
    reason_if_not_taken = Column(String, nullable=True)

class CostTracker(Base):
    __tablename__ = "cost_tracker"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_inr = Column(Float, default=0.0)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
