import pika
import redis
from django.conf import settings
from django.http import JsonResponse
from minio.error import S3Error
from pymongo.errors import PyMongoError

from common.mongo import mongo_service
from storage.services import minio_storage_service


def check_mongo():
    mongo_service.client().admin.command("ping")


def check_redis():
    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    client.ping()


def check_rabbitmq():
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=15,
            blocked_connection_timeout=5,
        )
    )
    try:
        channel = connection.channel()
        channel.queue_declare(queue=settings.QUEUE_USER_REGISTERED, passive=True)
    finally:
        connection.close()


def check_minio():
    # list_buckets checks MinIO availability without requiring the app bucket to exist yet.
    minio_storage_service.client().list_buckets()


def health_live(request):
    return JsonResponse({"status": "ok", "checks": {"process": "ok"}})


def health_ready(request):
    checks = {}
    check_functions = {
        "mongo": check_mongo,
        "redis": check_redis,
        "rabbitmq": check_rabbitmq,
        "minio": check_minio,
    }

    for name, check in check_functions.items():
        try:
            check()
            checks[name] = {"status": "ok"}
        except (PyMongoError, redis.RedisError, pika.exceptions.AMQPError, S3Error, OSError, Exception) as exc:
            checks[name] = {"status": "error", "detail": str(exc)}

    is_ready = all(item["status"] == "ok" for item in checks.values())
    return JsonResponse(
        {"status": "ok" if is_ready else "degraded", "checks": checks},
        status=200 if is_ready else 503,
    )


def health(request):
    live_response = {"process": "ok"}
    return JsonResponse({"status": "ok", "checks": live_response})
