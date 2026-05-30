import logging
import uuid

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

UNLOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class DistributedLock:
    def __init__(self):
        self._client = None

    def client(self):
        if self._client is None:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=0,
                socket_connect_timeout=1,
                socket_timeout=1,
                decode_responses=True,
            )
        return self._client

    def acquire(self, key: str, ttl_seconds: int = 30) -> str | bool | None:
        lock_id = str(uuid.uuid4())
        try:
            acquired = self.client().set(key, lock_id, ex=ttl_seconds, nx=True)
            return lock_id if acquired else False
        except Exception as exc:
            logger.warning("Redis lock unavailable for key=%s: %s", key, exc)
            return None

    def release(self, key: str, lock_id: str | None):
        if not lock_id:
            return
        try:
            self.client().eval(UNLOCK_SCRIPT, 1, key, lock_id)
        except Exception as exc:
            logger.warning("Redis lock release failed for key=%s: %s", key, exc)


distributed_lock = DistributedLock()
