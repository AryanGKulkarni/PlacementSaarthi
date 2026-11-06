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

    rabbitmq_url: str = "amqp://placement:placement@localhost:5672/"
    ingest_queue: str = "document_ingest"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()
