import logging
import uuid
from datetime import datetime, timezone

from django.conf import settings

from .rabbitmq_service import USER_REGISTERED_ROUTING_KEY, rabbitmq_service

logger = logging.getLogger(__name__)


def publish_user_registered(user):
    event = {
        "eventId": str(uuid.uuid4()),
        "eventType": "user.registered",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "userId": str(user.id),
            "email": user.email,
            "username": user.username,
            "displayName": user.display_name or user.username,
        },
        "metadata": {
            "attempt": 0,
            "source": "django-api",
        },
    }
    rabbitmq_service.publish(
        settings.RABBITMQ_EXCHANGE,
        USER_REGISTERED_ROUTING_KEY,
        event,
        options={"persistent": True},
    )
    logger.info("Published user.registered event for user_id=%s event_id=%s", user.id, event["eventId"])
    return event["eventId"]

