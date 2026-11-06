"""Thin RabbitMQ helpers (pika, blocking).

Queue: settings.ingest_queue (durable). Messages are persistent JSON.
"""

import json
import logging
import time

import pika
from pika.adapters.blocking_connection import BlockingChannel

from app.core.config import settings

log = logging.getLogger(__name__)


def _params(heartbeat: int = 60) -> pika.URLParameters:
    params = pika.URLParameters(settings.rabbitmq_url)
    params.heartbeat = heartbeat
    return params


def connect(heartbeat: int = 60, retries: int = 30, delay: float = 2.0) -> pika.BlockingConnection:
    """Open a connection, retrying while RabbitMQ is still starting up."""
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(_params(heartbeat))
        except pika.exceptions.AMQPConnectionError:
            if attempt == retries:
                raise
            log.warning("RabbitMQ not reachable (attempt %d/%d), retrying in %.0fs", attempt, retries, delay)
            time.sleep(delay)
    raise RuntimeError("unreachable")


def declare_queue(channel: BlockingChannel, queue: str) -> None:
    channel.queue_declare(queue=queue, durable=True)


def publish(queue: str, payload: dict) -> None:
    """Publish one persistent JSON message. Opens a short-lived connection (fine at our volume)."""
    connection = pika.BlockingConnection(_params())
    try:
        channel = connection.channel()
        declare_queue(channel, queue)
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(payload).encode(),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
    finally:
        connection.close()
