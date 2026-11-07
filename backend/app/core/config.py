from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://placement:placement@localhost:5432/placement_db"
    db_schema: str = "placement"
    db_echo: bool = False

    cors_origins: str = "http://localhost:5173"
    ollama_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    data_dir: Path = Path("./data")

    max_upload_mb: int = 20

    chunk_size: int = 1000      # characters per chunk
    chunk_overlap: int = 150    # characters carried into the next chunk
    min_chunk_chars: int = 20   # smaller chunks (stray headers/page numbers) are dropped

    embed_model: str = "nomic-embed-text"
    embed_batch_size: int = 32
    embed_timeout: float = 120.0  # seconds per batch request
    # nomic-embed-text expects task prefixes; set both to "" for models that don't
    embed_document_prefix: str = "search_document: "
    embed_query_prefix: str = "search_query: "

    chroma_host: str = "localhost"
    chroma_port: int = 8001  # host-mapped port; containers use chromadb:8000 via env
    chroma_collection: str = "knowledge_base"  # Chroma requires 3-512 chars

    rabbitmq_url: str = "amqp://placement:placement@localhost:5672/"
    ingest_queue: str = "document_ingest"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()
