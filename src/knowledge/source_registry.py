import sqlite3
import hashlib
import json
import numpy as np
from src.config import settings
from src.utils.logger import logger
from src.knowledge.chroma_client import get_collection

class SourceRegistry:
    def __init__(self):
        self.conn = sqlite3.connect(settings.sqlite_db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                source_id TEXT PRIMARY KEY,
                source_type TEXT,
                source_url TEXT,
                person TEXT,
                company TEXT,
                ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chunk_count INTEGER DEFAULT 0,
                collection_name TEXT,
                status TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def generate_source_id(self, identifier: str) -> str:
        return hashlib.md5(identifier.encode('utf-8')).hexdigest()

    def is_ingested(self, source_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM knowledge_sources WHERE source_id=?", (source_id,))
        row = cursor.fetchone()
        if row and row[0] == "complete":
            return True
        return False

    def register_source(self, data: dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_sources 
            (source_id, source_type, source_url, person, company, chunk_count, collection_name, status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data.get('source_id'),
            data.get('source_type'),
            data.get('source_url'),
            data.get('person'),
            data.get('company'),
            data.get('chunk_count', 0),
            data.get('collection_name'),
            data.get('status', 'pending')
        ))
        self.conn.commit()

    def update_status(self, source_id: str, status: str, chunk_count: int = None):
        cursor = self.conn.cursor()
        if chunk_count is not None:
            cursor.execute("UPDATE knowledge_sources SET status=?, chunk_count=?, last_updated=CURRENT_TIMESTAMP WHERE source_id=?", (status, chunk_count, source_id))
        else:
            cursor.execute("UPDATE knowledge_sources SET status=?, last_updated=CURRENT_TIMESTAMP WHERE source_id=?", (status, source_id))
        self.conn.commit()

    def get_ingestion_stats(self) -> dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT source_type, status, COUNT(*) FROM knowledge_sources GROUP BY source_type, status")
        stats = {}
        for row in cursor.fetchall():
            s_type, status, count = row
            if s_type not in stats:
                stats[s_type] = {}
            stats[s_type][status] = count
        return stats

    def get_pending_sources(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT source_id, source_url FROM knowledge_sources WHERE status='pending' OR status='processing'")
        return [{"source_id": r[0], "url": r[1]} for r in cursor.fetchall()]

    def is_duplicate_chunk(self, collection_name: str, vector: list, threshold: float = 0.95) -> bool:
        """
        Check if a near-identical chunk exists in the collection using Cosine Similarity.
        """
        try:
            coll = get_collection(collection_name)
        except Exception:
            return False

        try:
            # Requires the collection to have at least 1 element
            if coll.count() == 0:
                return False
                
            results = coll.query(query_embeddings=[vector], n_results=1, include=["embeddings", "distances"])
        except Exception as e:
            logger.debug(f"Chroma query failed during deduplication: {e}")
            return False
            
        embeddings = results.get('embeddings')
        if embeddings is None or len(embeddings) == 0 or len(embeddings[0]) == 0:
            return False

        matched_vector = results['embeddings'][0][0]
        
        v1 = np.array(vector)
        v2 = np.array(matched_vector)
        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            return False
            
        cos_sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        
        if cos_sim > threshold:
            logger.info(f"Duplicate chunk found (similarity: {cos_sim:.3f}). Skipping.")
            return True
            
        return False

source_registry = SourceRegistry()
