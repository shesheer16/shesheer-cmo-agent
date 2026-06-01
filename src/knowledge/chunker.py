import json
import re
import tiktoken
from typing import List, Dict, Any
from src.utils.logger import logger

class DocumentChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        # We use cl100k_base which is standard for accurate modern tokenization
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def get_token_count(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def _create_chunk_dict(self, text: str, metadata: dict, chunk_index: int, total_chunks: int, chunk_type: str) -> dict:
        # 4. Each chunk inherits all source_metadata
        chunk_meta = metadata.copy()
        
        # 5. Each chunk gets: chunk_id, chunk_index, total_chunks
        # 8. Add chunk_type field
        chunk_meta["chunk_index"] = chunk_index
        chunk_meta["total_chunks"] = total_chunks
        chunk_meta["chunk_type"] = chunk_type
        
        # Generating a simple deterministic chunk_id based on source if available
        base_id = metadata.get("source") or metadata.get("title") or metadata.get("person") or metadata.get("brand") or "doc"
        base_id = str(base_id).replace(" ", "_").lower()
        chunk_id = f"{base_id}_{chunk_type}_chunk_{chunk_index}"
        
        return {
            "chunk_id": chunk_id,
            "text": text,
            "metadata": chunk_meta
        }

    def chunk_document(self, text: str, source_metadata: dict, chunk_type: str = "section") -> List[Dict[str, Any]]:
        """
        Chunks a document based on the specified rules.
        """
        # 6. For structured annotations (JSON format), keep each insight as one complete chunk
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return self._chunk_json_list(data, source_metadata, chunk_type)
            elif isinstance(data, dict):
                return self._chunk_json_list([data], source_metadata, chunk_type)
        except json.JSONDecodeError:
            pass # Not a JSON, proceed to standard text chunking

        # 7. For long documents, chunk by section using heading detection (# ## ### patterns)
        return self._chunk_text_with_overlap(text, source_metadata, chunk_type)

    def _chunk_json_list(self, items: List[dict], metadata: dict, chunk_type: str) -> List[Dict[str, Any]]:
        """Keep each insight as one complete chunk (no splitting mid-insight)."""
        chunks = []
        total = len(items)
        for idx, item in enumerate(items):
            text_rep = json.dumps(item, indent=2)
            chunks.append(self._create_chunk_dict(text_rep, metadata, idx, total, chunk_type))
            
        logger.info(f"Chunked JSON into {total} structured insight chunks.")
        return chunks

    def _chunk_text_with_overlap(self, text: str, metadata: dict, chunk_type: str) -> List[Dict[str, Any]]:
        # Split by markdown headers, keeping the headers if possible
        # This regex matches lines that start with 1-3 hashes and keeps them attached to their section
        sections = re.split(r'(?m)^(?=#{1,3}\s+)', text)
        
        raw_chunks = []
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            
            # Check token count
            if self.get_token_count(sec) <= self.chunk_size:
                raw_chunks.append(sec)
            else:
                # 2. Chunk size: 400-600 tokens
                # 3. Overlap: 50 tokens
                raw_chunks.extend(self._split_by_tokens(sec))
                
        chunks = []
        total = len(raw_chunks)
        for idx, rc in enumerate(raw_chunks):
            chunks.append(self._create_chunk_dict(rc, metadata, idx, total, chunk_type))
            
        logger.info(f"Chunked text document into {total} chunks.")
        return chunks

    def _split_by_tokens(self, text: str) -> List[str]:
        tokens = self.encoder.encode(text)
        chunks = []
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
            start += (self.chunk_size - self.chunk_overlap)
        return chunks

chunker = DocumentChunker()
