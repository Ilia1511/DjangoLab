import logging
import os
import sys
import threading

from django.conf import settings

from .consumers import handle_user_registered
from .email_service import email_service
from .rabbitmq_service import rabbitmq_service

logger = logging.getLogger(__name__)

_started = False


def should_start_consumer() -> bool:
    if os.environ.get("START_RABBITMQ_CONSUMER", "").lower() == "true":
        return True
    if "runserver" not in sys.argv:
        return False
    if os.environ.get("RUN_MAIN") != "true":
        return False
    return True


def run_consumer_forever():
    try:
        email_service.validate_configuration()
        rabbitmq_service.consume(settings.QUEUE_USER_REGISTERED, handle_user_registered)
    except Exception:
        logger.exception("Critical RabbitMQ consumer failure. Exiting process for container restart.")
        os._exit(1)


def start_background_consumer_once():
    global _started
    if _started or not should_start_consumer():
        return
    _started = True
    thread = threading.Thread(target=run_consumer_forever, name="rabbitmq-consumer", daemon=True)
    thread.start()
    logger.info("RabbitMQ background consumer thread scheduled.")
