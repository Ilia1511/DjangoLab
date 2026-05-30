import logging

from django.conf import settings

from common.cache import cache_service

from .email_service import email_service
from .rabbitmq_service import USER_REGISTERED_ROUTING_KEY, RabbitMQMessage, rabbitmq_service

logger = logging.getLogger(__name__)

PROCESSED_EVENT_TTL_SECONDS = 24 * 60 * 60
MAX_ATTEMPTS = 3


def processed_key(event_id: str) -> str:
    return f"wp:events:processed:{event_id}"


def is_event_processed(event_id: str) -> bool:
    return cache_service.exists(processed_key(event_id)) is True


def mark_event_as_processed(event_id: str):
    cache_service.set(processed_key(event_id), {"processed": True}, ttl=PROCESSED_EVENT_TTL_SECONDS)


def handle_user_registered(message: RabbitMQMessage):
    event = message.content
    event_id = event.get("eventId")
    payload = event.get("payload") or {}
    metadata = event.get("metadata") or {}
    attempt = int(metadata.get("attempt", 0))

    if not event_id:
        logger.error("Received user.registered event without eventId. Sending to DLQ.")
        rabbitmq_service.nack(message, requeue=False)
        return

    if is_event_processed(event_id):
        logger.info("Skipping already processed event_id=%s", event_id)
        rabbitmq_service.ack(message)
        return

    logger.info("Received user.registered event_id=%s attempt=%s", event_id, attempt + 1)
    try:
        logger.info("Sending welcome email for event_id=%s user_id=%s", event_id, payload.get("userId"))
        email_service.send_welcome_email(
            to=payload["email"],
            display_name=payload.get("displayName") or payload.get("username") or payload["email"],
            user_id=payload["userId"],
        )
        mark_event_as_processed(event_id)
        rabbitmq_service.ack(message)
        logger.info("Welcome email sent and event acknowledged: event_id=%s", event_id)
    except Exception as exc:
        if attempt + 1 >= MAX_ATTEMPTS:
            logger.error("Event %s failed after %s attempts. Sending to DLQ: %s", event_id, MAX_ATTEMPTS, exc)
            rabbitmq_service.nack(message, requeue=False)
            return

        retry_event = {
            **event,
            "metadata": {
                **metadata,
                "attempt": attempt + 1,
            },
        }
        rabbitmq_service.publish(
            settings.RABBITMQ_EXCHANGE,
            USER_REGISTERED_ROUTING_KEY,
            retry_event,
            options={"persistent": True},
        )
        rabbitmq_service.ack(message)
        logger.warning("Retry scheduled for event_id=%s next_attempt=%s", event_id, attempt + 2)
