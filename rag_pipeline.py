import re
import numpy as np
from llm_provider import LLM


class RAGPipeline:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: list[str] = []
        self.embeddings: np.ndarray | None = None

    # ---------- Ingestion ----------

    def _split_into_chunks(self, text: str) -> list[str]:
        """Simple sliding-window chunking on whitespace-normalized text."""
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        words = text.split(" ")
        chunks = []
        step = max(self.chunk_size - self.chunk_overlap, 1)

        for i in range(0, len(words), step):
            chunk_words = words[i : i + self.chunk_size]
            if not chunk_words:
                break
            chunks.append(" ".join(chunk_words))
            if i + self.chunk_size >= len(words):
                break
        return chunks

    def ingest(self, texts: list[str]):
        """Add one or more documents (raw strings) to the knowledge base."""
        new_chunks = []
        for text in texts:
            new_chunks.extend(self._split_into_chunks(text))

        if not new_chunks:
            return

        new_embeddings = []
        for chunk in new_chunks:
            new_embeddings.append(LLM.encode(chunk))

        self.chunks.extend(new_chunks)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

    # ---------- Retrieval ----------

    def retrieve_context(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        query_emb = LLM.encode(query)
        query_emb /= np.linalg.norm(query_emb)

        # Cosine similarity == dot product since embeddings are normalized
        scores = self.embeddings @ query_emb
        top_k = min(top_k, len(self.chunks))
        top_idx = np.argsort(scores)[::-1][:top_k]
        context = ''
        for i in top_idx:
            context += self.chunks[i] + "\n\n"
        return context

    # ---------- Generation ----------

    def answer(self, query: str) -> str:
        context = self.retrieve(query, top_k=top_k)
        if not context:
            return "I don't have any ingested content to answer from yet."

        prompt = (
            "Answer the question using only the context below. "
            "If the answer isn't in the context, say you don't know.\n\n"
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        )

        output = LLM.generate(user_prompt=prompt)
        return output