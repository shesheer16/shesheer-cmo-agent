"""
ChromaDB Client Manager for Shesheer CMO Agent.

Expected Metadata Schemas per Collection:

1. founders_mindsets
   metadata: {person, company, topic, market_phase, insight_type, applicable_segment, year, indian_applicable, contradicts_western}

2. campaign_case_studies
   metadata: {brand, campaign_name, year, agency, cultural_insight, mental_model, outcome, sector, applicable_domains}

3. cmo_profiles
   metadata: {name, company, sector, strategy_type, market_phase, achievement}

4. market_data_reports
   metadata: {source, year, data_type, sector, market_segment, verified}

5. consumer_psychology
   metadata: {researcher, institution, research_area, applicable_segment, finding_type}

6. books_annotations
   metadata: {title, author, chapter, topic, indian_applicable, market_phase}

7. social_intelligence
   metadata: {source, person, platform, date, topic, content_type}

8. startup_context
   metadata: {context_type, date, category, verified}
"""

import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import settings
from src.utils.logger import logger

class ChromaClientManager:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            # Ensure path exists
            os.makedirs(settings.chroma_db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            logger.info(f"Initialized ChromaDB PersistentClient at {settings.chroma_db_path}")
            self._ensure_collections()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

    def _ensure_collections(self):
        """Creates the 8 core collections if they don't exist."""
        collections = [
            "founders_mindsets",
            "campaign_case_studies",
            "cmo_profiles",
            "market_data_reports",
            "consumer_psychology",
            "books_annotations",
            "social_intelligence",
            "startup_context"
        ]
        
        for name in collections:
            try:
                # get_or_create_collection automatically handles existence check
                # Note: ChromaDB doesn't strictly enforce schema on collection creation,
                # but we document the expected metadata fields above for reference.
                self.client.get_or_create_collection(name=name)
                logger.debug(f"Verified collection: {name}")
            except Exception as e:
                logger.error(f"Failed to verify/create collection {name}: {e}")

    def get_collection(self, name: str):
        """Helper function to get a specific collection."""
        if not self.client:
            raise RuntimeError("ChromaDB client is not initialized.")
        try:
            return self.client.get_collection(name=name)
        except Exception as e:
            logger.error(f"Collection {name} not found or error accessing it: {e}")
            raise

    def list_collections(self):
        """Helper function to list all collections."""
        if not self.client:
            raise RuntimeError("ChromaDB client is not initialized.")
        return self.client.list_collections()

# Expose a singleton manager instance and module-level helpers
chroma_manager = ChromaClientManager()

def get_collection(name: str):
    return chroma_manager.get_collection(name)

def list_collections():
    return chroma_manager.list_collections()
