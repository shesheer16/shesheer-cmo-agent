import time
import google.genai as genai
from src.config import settings
from src.utils.logger import logger

class Embedder:
    def __init__(self):
        """Initialize Gemini text-embedding-004 API client."""
        logger.info("Initializing Gemini Embeddings (text-embedding-004)...")
        
        if not settings.gemini_api_key or settings.gemini_api_key == "your_key_here":
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = "text-embedding-004"
        self.rate_limit_delay = 0.5  # 500ms between requests
        self.last_request_time = 0
        
        logger.info("✓ Gemini Embeddings ready (text-embedding-004)")

    def _respect_rate_limit(self):
        """Enforce rate limiting (60 RPM = 1 per second max)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def embed(self, text: str) -> list:
        """Embed a single text string using Gemini API."""
        try:
            self._respect_rate_limit()
            
            result = genai.embed_content(
                model=self.model,
                content=text
            )
            
            embedding = result['embedding']
            return embedding
            
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            return []

    def embed_batch(self, texts: list, batch_size: int = 10) -> list:
        """
        Embed multiple texts efficiently with batching and rate limiting.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process per batch (default 10)
        
        Returns:
            List of embeddings
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            for text in batch:
                try:
                    embedding = self.embed(text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Batch embedding failed for chunk {i}: {e}")
                    embeddings.append([])
            
            # Log progress
            if (i + batch_size) % 50 == 0:
                logger.info(f"Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks")
        
        logger.info(f"✓ Batch embedding complete: {len([e for e in embeddings if e])} successful")
        return embeddings

# Singleton instance
embedder = Embedder()