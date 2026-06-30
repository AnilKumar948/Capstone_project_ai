from __future__ import annotations

import asyncio
from collections.abc import Sequence

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

from app.config import get_settings


class EmbedderService:
    def __init__(self):
        settings = get_settings()
        self.index_name = settings.pinecone_index
        self.pc = Pinecone(api_key=settings.pinecone_api_key) if settings.pinecone_api_key else None
        self.index = None
        
        if settings.use_litellm:
            # Use LiteLLM for embeddings
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                model=settings.litellm_embedding_model,
                api_key=settings.litellm_api_key,
                base_url=settings.litellm_proxy_url,
            )
        else:
            # Use OpenAI directly
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key,
            )

    def _get_index(self):
        if self.index is not None:
            return self.index
        if not self.pc:
            return None
        try:
            self.index = self.pc.Index(self.index_name)
            return self.index
        except Exception:
            return None

    async def embed_chunks(self, job_id: str, chunks: Sequence[str]) -> list[dict]:
        """Embed chunks with OpenAI or skip if key is invalid."""
        vectors = None
        try:
            vectors = await self.embeddings.aembed_documents(list(chunks))
        except Exception as e:
            # If embedding fails (e.g., invalid API key), use dummy vectors
            import logging
            logging.warning(f"Embedding failed: {e}. Using placeholder vectors.")
            # Create dummy vectors for compatibility (matching embedding-3-small dimension)
            vectors = [[0.0] * 1536 for _ in chunks]
        
        records: list[dict] = []
        for idx, vector in enumerate(vectors):
            text = str(chunks[idx])
            records.append(
                {
                    "id": f"{job_id}:{idx}",
                    "values": vector,
                    "metadata": {
                        "job_id": job_id,
                        "chunk_index": idx,
                        "clause_type": "GENERAL",
                        "text": text[:600],
                    },
                }
            )
        index = self._get_index()
        if index:
            await asyncio.to_thread(index.upsert, vectors=records)
        return records

    async def search_clauses(self, query: str, top_k: int = 5) -> list[dict]:
        index = self._get_index()
        if not index:
            return []
        try:
            query_vector = await self.embeddings.aembed_query(query)
        except Exception as e:
            # If embedding query fails (e.g., invalid API key), return empty results
            import logging
            logging.warning(f"Query embedding failed: {e}. Returning empty results.")
            return []
        
        result = await asyncio.to_thread(
            index.query,
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )
        matches = result.get("matches", []) if isinstance(result, dict) else getattr(result, "matches", [])
        output: list[dict] = []
        for match in matches:
            metadata = match.get("metadata", {}) if isinstance(match, dict) else getattr(match, "metadata", {})
            score = match.get("score", 0.0) if isinstance(match, dict) else getattr(match, "score", 0.0)
            output.append(
                {
                    "job_id": metadata.get("job_id"),
                    "clause_type": metadata.get("clause_type", "GENERAL"),
                    "snippet": metadata.get("text", ""),
                    "score": score,
                }
            )
        return output
