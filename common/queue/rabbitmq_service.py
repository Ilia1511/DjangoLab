import json
import logging
from dataclasses import dataclass
from typing import Callable

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

USER_REGISTERED_ROUTING_KEY = "user.registered"


@dataclass
class RabbitMQMessage:
    content: dict
    method: object
    properties: pika.BasicProperties
    channel: object


class RabbitMQService:
    def __init__(self):
        self._connection = None
        self._channel = None

    def _parameters(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
        return pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=30,
        )

    def connect(self):
        if self._connection and self._connection.is_open and self._channel and self._channel.is_open:
            return self._connection, self._channel
        self._connection = pika.BlockingConnection(self._parameters())
        self._channel = self._connection.channel()
        self.declare_topology(self._channel)
        return self._connection, self._channel

    def new_connection(self):
        connection = pika.BlockingConnection(self._parameters())
        channel = connection.channel()
        self.declare_topology(channel)
        return connection, channel

    def declare_topology(self, channel=None):
        channel = channel or self.connect()[1]
        channel.exchange_declare(exchange=settings.RABBITMQ_EXCHANGE, exchange_type="direct", durable=True)
        channel.exchange_declare(exchange=settings.RABBITMQ_DLX, exchange_type="direct", durable=True)
        channel.queue_declare(
            queue=settings.QUEUE_USER_REGISTERED,
            durable=True,
            arguments={
                "x-dead-letter-exchange": settings.RABBITMQ_DLX,
                "x-dead-letter-routing-key": USER_REGISTERED_ROUTING_KEY,
            },
        )
        channel.queue_bind(
            queue=settings.QUEUE_USER_REGISTERED,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key=USER_REGISTERED_ROUTING_KEY,
        )
        dlq_name = f"{settings.QUEUE_USER_REGISTERED}.dlq"
        channel.queue_declare(queue=dlq_name, durable=True)
        channel.queue_bind(queue=dlq_name, exchange=settings.RABBITMQ_DLX, routing_key=USER_REGISTERED_ROUTING_KEY)

    def publish(self, exchange: str, routing_key: str, payload: dict, options: dict | None = None):
        connection, channel = self.new_connection()
        options = options or {}
        properties = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2 if options.get("persistent", True) else 1,
        )
        try:
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
                properties=properties,
                mandatory=True,
            )
            logger.info("RabbitMQ event published: exchange=%s routing_key=%s event_id=%s", exchange, routing_key, payload.get("eventId"))
        finally:
            connection.close()

    def consume(self, queue: str, handler: Callable[[RabbitMQMessage], None]):
        _, channel = self.connect()
        channel.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):
            try:
                content = json.loads(body.decode("utf-8"))
            except Exception:
                logger.exception("RabbitMQ message JSON decoding failed. Sending to DLQ.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            message = RabbitMQMessage(content=content, method=method, properties=properties, channel=ch)
            try:
                handler(message)
            except Exception:
                logger.exception("Unhandled RabbitMQ consumer error. Sending message back to queue.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)
        logger.info("RabbitMQ consumer started: queue=%s", queue)
        channel.start_consuming()

    def ack(self, message: RabbitMQMessage):
        message.channel.basic_ack(delivery_tag=message.method.delivery_tag)

    def nack(self, message: RabbitMQMessage, requeue: bool):
        message.channel.basic_nack(delivery_tag=message.method.delivery_tag, requeue=requeue)

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()


rabbitmq_service = RabbitMQService()
