import logging
import uuid
from datetime import datetime, timezone

from django.conf import settings
from django.utils.text import get_valid_filename
from minio import Minio
from minio.error import S3Error

from common.cache import cache_service
from common.mongo import mongo_service

logger = logging.getLogger(__name__)

ALLOWED_AVATAR_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}


def utcnow():
    return datetime.now(timezone.utc)


class MinioStorageService:
    def __init__(self):
        self._client = None

    def client(self):
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL,
            )
        return self._client

    def ensure_bucket(self):
        client = self.client()
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)

    def upload_file(self, stream, object_key: str, size: int, mimetype: str):
        self.ensure_bucket()
        if hasattr(stream, "seek"):
            stream.seek(0)
        self.client().put_object(
            settings.MINIO_BUCKET,
            object_key,
            stream,
            length=size,
            content_type=mimetype,
        )

    def get_file_stream(self, object_key: str):
        return self.client().get_object(settings.MINIO_BUCKET, object_key)

    def delete_file(self, object_key: str) -> bool:
        try:
            self.client().remove_object(settings.MINIO_BUCKET, object_key)
            return True
        except S3Error as exc:
            logger.warning("MinIO object delete failed for %s: %s", object_key, exc)
            return False

    def file_exists(self, object_key: str) -> bool:
        try:
            self.client().stat_object(settings.MINIO_BUCKET, object_key)
            return True
        except S3Error:
            return False


minio_storage_service = MinioStorageService()


class FileService:
    @staticmethod
    def collection():
        return mongo_service.db().files

    @staticmethod
    def build_meta_cache_key(file_id: str) -> str:
        return f"wp:files:{file_id}:meta"

    @staticmethod
    def public_payload(doc: dict) -> dict:
        return {
            "id": doc["_id"],
            "userId": doc["userId"],
            "originalName": doc["originalName"],
            "size": doc["size"],
            "mimetype": doc["mimetype"],
            "isUsed": doc.get("isUsed", False),
            "createdAt": doc["createdAt"].isoformat() if hasattr(doc["createdAt"], "isoformat") else doc["createdAt"],
            "updatedAt": doc["updatedAt"].isoformat() if hasattr(doc["updatedAt"], "isoformat") else doc["updatedAt"],
        }

    @staticmethod
    def validate_upload(uploaded_file):
        if uploaded_file.size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File is too large. Maximum size is {settings.MAX_FILE_SIZE} bytes.")
        mimetype = uploaded_file.content_type or "application/octet-stream"
        if mimetype not in ALLOWED_AVATAR_MIME_TYPES:
            raise ValueError("Only PNG and JPEG images are allowed.")

    @staticmethod
    def upload_file(uploaded_file, user) -> dict:
        FileService.validate_upload(uploaded_file)
        file_id = str(uuid.uuid4())
        safe_name = get_valid_filename(uploaded_file.name or "upload")
        mimetype = uploaded_file.content_type or "application/octet-stream"
        object_key = f"users/{user.id}/{file_id}/{safe_name}"

        minio_storage_service.upload_file(uploaded_file.file, object_key, uploaded_file.size, mimetype)

        now = utcnow()
        doc = {
            "_id": file_id,
            "userId": str(user.id),
            "originalName": uploaded_file.name or safe_name,
            "objectKey": object_key,
            "size": uploaded_file.size,
            "mimetype": mimetype,
            "bucket": settings.MINIO_BUCKET,
            "isUsed": False,
            "createdAt": now,
            "updatedAt": now,
            "deletedAt": None,
        }
        FileService.collection().insert_one(doc)
        cache_service.set(FileService.build_meta_cache_key(file_id), doc, ttl=300)
        return doc

    @staticmethod
    def get_file(file_id: str, user_id: str | None = None, use_cache: bool = True) -> dict | None:
        cache_key = FileService.build_meta_cache_key(file_id)
        doc = cache_service.get(cache_key) if use_cache else None
        if doc is None:
            query = {"_id": str(file_id), "deletedAt": None}
            if user_id is not None:
                query["userId"] = str(user_id)
            doc = FileService.collection().find_one(query)
            if doc:
                cache_service.set(cache_key, doc, ttl=300)
        elif user_id is not None and doc.get("userId") != str(user_id):
            return None
        return doc

    @staticmethod
    def delete_file(file_id: str, user_id: str) -> bool:
        doc = FileService.get_file(file_id, user_id=user_id)
        if not doc:
            return False

        minio_storage_service.delete_file(doc["objectKey"])
        FileService.collection().update_one(
            {"_id": str(file_id), "userId": str(user_id), "deletedAt": None},
            {"$set": {"deletedAt": utcnow(), "updatedAt": utcnow()}},
        )
        cache_service.delete(FileService.build_meta_cache_key(file_id))
        return True

    @staticmethod
    def user_owns_file(file_id: str, user_id: str) -> bool:
        return FileService.get_file(str(file_id), user_id=str(user_id)) is not None

    @staticmethod
    def mark_usage(file_id: str | None, user_id: str, is_used: bool):
        if not file_id:
            return
        FileService.collection().update_one(
            {"_id": str(file_id), "userId": str(user_id), "deletedAt": None},
            {"$set": {"isUsed": is_used, "updatedAt": utcnow()}},
        )
        cache_service.delete(FileService.build_meta_cache_key(str(file_id)))
