"""Ingestion worker: consumes document ids from RabbitMQ and ingests them.

Run:  python -m app.workers.ingestion_worker
"""

import json
import logging
import signal
import uuid

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging import rabbitmq
from app.repositories.document_repository import DocumentRepository
from app.rag.ingestion_service import IngestionService

log = logging.getLogger("ingestion_worker")

# Ingesting a big file can take minutes while pika's blocking loop isn't servicing
# heartbeats, so use a long heartbeat to stop RabbitMQ dropping the connection.
HEARTBEAT_SECONDS = 600


def handle_message(channel, method, properties, body: bytes) -> None:
    try:
        document_id = uuid.UUID(json.loads(body)["document_id"])
    except (ValueError, KeyError, TypeError):
        log.error("Dropping malformed message: %r", body[:200])
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        with SessionLocal() as db:
            IngestionService(DocumentRepository(db)).process(document_id)
    except Exception:
        # DB down etc.: the document status couldn't even be recorded.
        # Requeue once; drop if it was already redelivered to avoid a hot loop.
        log.exception("Unexpected error for %s", document_id)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=not method.redelivered)
        return

    channel.basic_ack(delivery_tag=method.delivery_tag)


def _raise_keyboard_interrupt(*_):
    raise KeyboardInterrupt


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("pika").setLevel(logging.WARNING)
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)  # `docker stop` -> clean shutdown

    connection = rabbitmq.connect(heartbeat=HEARTBEAT_SECONDS)
    channel = connection.channel()
    rabbitmq.declare_queue(channel, settings.ingest_queue)
    channel.basic_qos(prefetch_count=1)  # one document at a time
    channel.basic_consume(queue=settings.ingest_queue, on_message_callback=handle_message)

    log.info("Waiting for jobs on queue '%s'", settings.ingest_queue)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        log.info("Shutting down")
        channel.stop_consuming()
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
