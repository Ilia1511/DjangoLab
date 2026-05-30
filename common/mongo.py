import logging

from django.conf import settings
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class MongoService:
    def __init__(self):
        self._client = None
        self._db = None

    def client(self):
        if self._client is None:
            self._client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
        return self._client

    def db(self):
        if self._db is None:
            self._db = self.client()[settings.MONGO_DB_NAME]
            self.ensure_indexes()
        return self._db

    def ensure_indexes(self):
        try:
            db = self.client()[settings.MONGO_DB_NAME]
            db.users.create_index([("email", ASCENDING)], unique=True)
            db.users.create_index([("username", ASCENDING)], unique=True)
            db.users.create_index([("yandexId", ASCENDING)], unique=True, sparse=True)
            db.tokens.create_index([("tokenHash", ASCENDING)], unique=True)
            db.tokens.create_index([("userId", ASCENDING), ("isRevoked", ASCENDING)])
            db.quests.create_index([("owner.id", ASCENDING), ("deletedAt", ASCENDING)])
            db.quests.create_index([("title", ASCENDING), ("deletedAt", ASCENDING)])
            db.files.create_index([("userId", ASCENDING), ("deletedAt", ASCENDING)])
            db.files.create_index([("objectKey", ASCENDING)], unique=True)
        except PyMongoError as exc:
            logger.warning("Mongo index initialization failed: %s", exc)


mongo_service = MongoService()
