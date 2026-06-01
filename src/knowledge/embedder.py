import time
from typing import List
from sentence_transformers import SentenceTransformer
from langdetect import detect, DetectorFactory
from src.utils.logger import logger

# Ensure consistent language detection
DetectorFactory.seed = 0

class Embedder:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            cls._instance.en_model = None
            cls._instance.multi_model = None
        return cls._instance

    def _load_en_model(self):
        if self.en_model is None:
            logger.info("Loading English embedding model: all-MiniLM-L6-v2")
            self.en_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self.en_model

    def _load_multi_model(self):
        if self.multi_model is None:
            logger.info("Loading multilingual embedding model: intfloat/multilingual-e5-large")
            self.multi_model = SentenceTransformer("intfloat/multilingual-e5-large")
        return self.multi_model

    def detect_language(self, text: str) -> str:
        try:
            return detect(text)
        except Exception as e:
            logger.warning(f"Language detection failed, defaulting to 'en'. Error: {e}")
            return "en"

    def embed(self, text: str) -> List[float]:
        """Embeds a single string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of strings, routing them based on the first text's language."""
        if not texts:
            return []

        start_time = time.time()
        
        # We detect the language of the first text to decide the model for the whole batch
        # This assumes batches are homogeneous in language.
        first_text = texts[0]
        lang = self.detect_language(first_text)

        if lang == "en":
            model = self._load_en_model()
            model_name = "all-MiniLM-L6-v2"
            texts_to_embed = texts
        else:
            model = self._load_multi_model()
            model_name = "intfloat/multilingual-e5-large"
            # E5 models generally require a 'passage: ' prefix for document embeddings
            texts_to_embed = [f"passage: {t}" for t in texts]

        # Convert to a standard Python list of floats
        embeddings = model.encode(texts_to_embed, convert_to_numpy=True).tolist()
        
        elapsed = time.time() - start_time
        logger.info(f"Embedded batch of {len(texts)} items using {model_name} in {elapsed:.3f}s")
        
        return embeddings

# Singleton instance
embedder = Embedder()

def test_embedding():
    logger.info("Starting embedding test...")
    
    en_text = "Physics Wallah disrupted the Indian edtech market with extreme affordability."
    hi_text = "फिजिक्स वाला ने भारतीय एडटेक बाजार को सस्ती शिक्षा से बदल दिया।"
    
    en_vec = embedder.embed(en_text)
    logger.info(f"English vector shape: {len(en_vec)} dimensions")
    
    hi_vec = embedder.embed(hi_text)
    logger.info(f"Hindi vector shape: {len(hi_vec)} dimensions")

if __name__ == "__main__":
    test_embedding()
