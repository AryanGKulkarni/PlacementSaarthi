import uuid

from app.core.config import settings
from app.messaging import rabbitmq


class IngestQueue:
    """Publishes 'please ingest this document' jobs for the ingestion worker."""

    def enqueue(self, document_id: uuid.UUID) -> None:
        rabbitmq.publish(settings.ingest_queue, {"document_id": str(document_id)})
