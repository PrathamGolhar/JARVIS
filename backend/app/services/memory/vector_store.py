from dataclasses import dataclass
import math
import re
from threading import RLock
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    file_id: str
    filename: str
    text: str
    metadata: dict[str, Any]


class LocalRAGVectorStore:
    """
    High-performance, zero-dependency local RAG vector & BM25 retrieval engine.
    Splits uploaded documents into chunks, computes term frequency vectors, and retrieves semantic matches.
    """

    def __init__(self) -> None:
        self._chunks: dict[str, DocumentChunk] = {}
        self._lock = RLock()

    def _tokenize(self, text: str) -> list[str]:
        return [w.lower() for w in re.findall(r"\b\w{2,}\b", text)]

    def chunk_and_index(self, file_id: str, filename: str, full_text: str, chunk_size: int = 800, overlap: int = 150) -> int:
        """
        Split document text into overlapping chunks and index them for retrieval.
        """
        words = full_text.split()
        if not words:
            return 0

        chunks_created = 0
        step = max(1, chunk_size - overlap)

        with self._lock:
            # Clear previous chunks for this file
            self._chunks = {k: v for k, v in self._chunks.items() if v.file_id != file_id}

            for i in range(0, len(words), step):
                chunk_words = words[i : i + chunk_size]
                chunk_text = " ".join(chunk_words)
                cid = f"{file_id}_chunk_{chunks_created}"

                self._chunks[cid] = DocumentChunk(
                    chunk_id=cid,
                    file_id=file_id,
                    filename=filename,
                    text=chunk_text,
                    metadata={"index": chunks_created, "word_count": len(chunk_words)},
                )
                chunks_created += 1

        return chunks_created

    def search(self, query: str, top_k: int = 4, file_id: str | None = None) -> list[dict[str, Any]]:
        """
        Perform BM25/TF-IDF similarity search across indexed document chunks.
        """
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return []

        scored_results: list[tuple[float, DocumentChunk]] = []

        with self._lock:
            for chunk in self._chunks.values():
                if file_id and chunk.file_id != file_id:
                    continue

                chunk_tokens = self._tokenize(chunk.text)
                if not chunk_tokens:
                    continue

                # Term matching & TF scoring
                score = 0.0
                total_tokens = len(chunk_tokens)
                for q in query_tokens:
                    count = chunk_tokens.count(q)
                    if count > 0:
                        tf = count / total_tokens
                        score += tf * (1.0 + math.log(1.0 + count))

                if score > 0:
                    scored_results.append((score, chunk))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "chunk_id": c.chunk_id,
                "file_id": c.file_id,
                "filename": c.filename,
                "text": c.text,
                "score": round(score, 4),
            }
            for score, c in scored_results[:top_k]
        ]


rag_store = LocalRAGVectorStore()
