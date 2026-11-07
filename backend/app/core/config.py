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

    jwt_secret: str = "dev-insecure-secret-change-me"  # set JWT_SECRET in .env
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Default admin, created on startup when no admin user exists
    admin_email: str = "admin@admin.com"
    admin_password: str = "admin"

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

    retrieval_top_k: int = 4                 # chunks finally passed to the LLM
    retrieval_fetch_k: int = 8               # fetched from Chroma before filtering/dedup
    retrieval_max_distance: float = 0.6      # cosine distance; larger = treated as irrelevant
    retrieval_max_per_doc: int = 2           # stop one document taking every slot
    retrieval_max_context_chars: int = 6000  # total chunk text budget (~1,500 tokens)
    max_question_chars: int = 500

    rabbitmq_url: str = "amqp://placement:placement@localhost:5672/"
    ingest_queue: str = "document_ingest"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()
