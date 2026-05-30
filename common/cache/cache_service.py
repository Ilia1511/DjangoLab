import json
import logging
from typing import Any

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self._client = None
        self._enabled = True
        # API alias for specs that expect `del(key)`.
        setattr(self, "del", self.delete)
        self._connect()

    def _connect(self):
        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=0,
                socket_connect_timeout=1,
                socket_timeout=1,
                decode_responses=True,
            )
            self._client.ping()
            self._enabled = True
        except Exception as exc:
            self._enabled = False
            self._client = None
            logger.warning("Redis is unavailable. Cache will be optional: %s", exc)

    def _ensure_client(self):
        if not self._enabled or self._client is None:
            self._connect()
        return self._client

    def get(self, key: str) -> Any | None:
        client = self._ensure_client()
        if client is None:
            return None
        try:
            value = client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:
            logger.warning("Redis get failed for key=%s: %s", key, exc)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        client = self._ensure_client()
        if client is None:
            return False
        try:
            payload = json.dumps(value, ensure_ascii=False, default=str)
            ttl_to_use = ttl if ttl is not None else settings.CACHE_TTL_DEFAULT
            client.set(key, payload, ex=ttl_to_use)
            return True
        except Exception as exc:
            logger.warning("Redis set failed for key=%s: %s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        client = self._ensure_client()
        if client is None:
            return False
        try:
            client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Redis delete failed for key=%s: %s", key, exc)
            return False

    def delByPattern(self, pattern: str) -> int:
        client = self._ensure_client()
        if client is None:
            return 0
        deleted = 0
        try:
            keys = list(client.scan_iter(match=pattern, count=200))
            if keys:
                deleted = client.unlink(*keys)
            return deleted
        except Exception as exc:
            logger.warning("Redis pattern delete failed for pattern=%s: %s", pattern, exc)
            return 0

    def exists(self, key: str) -> bool | None:
        client = self._ensure_client()
        if client is None:
            return None
        try:
            return bool(client.exists(key))
        except Exception as exc:
            logger.warning("Redis exists failed for key=%s: %s", key, exc)
            return None


cache_service = CacheService()
