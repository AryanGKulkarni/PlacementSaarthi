"""Text -> vectors using an Ollama embedding model (default: nomic-embed-text).

Documents and queries are embedded with different task prefixes, as the
nomic model expects ("search_document: ..." vs "search_query: ...").
"""

import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Ollama couldn't produce embeddings (down, model missing, bad response)."""


class Embedder:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        batch_size: int | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.embed_model
        self.batch_size = batch_size or settings.embed_batch_size
        self.timeout = timeout or settings.embed_timeout

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed chunks for storage. Returns one vector per text, in the same order."""
        prefixed = [settings.embed_document_prefix + t for t in texts]
        vectors: list[list[float]] = []
        with httpx.Client(timeout=self.timeout) as client:
            for start in range(0, len(prefixed), self.batch_size):
                batch = prefixed[start : start + self.batch_size]
                vectors.extend(self._embed(client, batch))
                log.debug("Embedded %d/%d chunks", len(vectors), len(prefixed))
        self._check_dimensions(vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed a user question for similarity search."""
        with httpx.Client(timeout=self.timeout) as client:
            return self._embed(client, [settings.embed_query_prefix + text])[0]

    def _embed(self, client: httpx.Client, inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        try:
            response = client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": inputs, "truncate": True},
            )
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Ollama not reachable at {self.base_url}: {exc}") from exc

        if response.status_code == 404:
            raise EmbeddingError(
                f"Embedding model '{self.model}' not found in Ollama. "
                f"Run: docker compose exec ollama ollama pull {self.model}"
            )
        if response.status_code != 200:
            raise EmbeddingError(f"Ollama error {response.status_code}: {response.text[:300]}")

        embeddings = response.json().get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
            raise EmbeddingError(
                f"Expected {len(inputs)} embeddings, got "
                f"{len(embeddings) if isinstance(embeddings, list) else 'none'}"
            )
        return embeddings

    @staticmethod
    def _check_dimensions(vectors: list[list[float]]) -> None:
        dims = {len(v) for v in vectors}
        if len(dims) > 1:
            raise EmbeddingError(f"Inconsistent embedding dimensions: {sorted(dims)}")
