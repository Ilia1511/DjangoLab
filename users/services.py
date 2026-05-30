import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from pymongo.errors import DuplicateKeyError

from common.cache import cache_service
from common.mongo import mongo_service


def utcnow():
    return datetime.now(timezone.utc)


NOT_PROVIDED = object()


def public_user_payload(user) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_file_id": user.avatar_file_id,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "is_active": user.is_active,
    }


@dataclass
class MongoUser:
    id: str
    username: str
    email: str
    password_hash: str = ""
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    display_name: str = ""
    bio: str = ""
    avatar_file_id: str | None = None
    yandex_id: str | None = None
    date_joined: datetime | None = None
    is_active: bool = True
    deleted_at: datetime | None = None

    @property
    def pk(self):
        return self.id

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)


class UserService:
    @staticmethod
    def collection():
        return mongo_service.db().users

    @staticmethod
    def from_doc(doc: dict | None) -> MongoUser | None:
        if not doc:
            return None
        return MongoUser(
            id=str(doc["_id"]),
            username=doc.get("username", ""),
            email=doc.get("email", ""),
            password_hash=doc.get("passwordHash", ""),
            first_name=doc.get("firstName", ""),
            last_name=doc.get("lastName", ""),
            phone=doc.get("phone", ""),
            display_name=doc.get("displayName", ""),
            bio=doc.get("bio", ""),
            avatar_file_id=doc.get("avatarFileId"),
            yandex_id=doc.get("yandexId"),
            date_joined=doc.get("dateJoined"),
            is_active=doc.get("isActive", True),
            deleted_at=doc.get("deletedAt"),
        )

    @staticmethod
    def get_by_id(user_id: str) -> MongoUser | None:
        try:
            doc = UserService.collection().find_one({"_id": ObjectId(user_id), "deletedAt": None})
        except Exception:
            return None
        return UserService.from_doc(doc)

    @staticmethod
    def get_by_email(email: str) -> MongoUser | None:
        doc = UserService.collection().find_one({"email": email.lower(), "deletedAt": None})
        return UserService.from_doc(doc)

    @staticmethod
    def username_exists(username: str) -> bool:
        return UserService.collection().count_documents({"username": username, "deletedAt": None}, limit=1) > 0

    @staticmethod
    def email_exists(email: str) -> bool:
        return UserService.collection().count_documents({"email": email.lower(), "deletedAt": None}, limit=1) > 0

    @staticmethod
    def create_user(username: str, email: str, password: str, phone: str = "") -> MongoUser:
        now = utcnow()
        doc = {
            "username": username,
            "email": email.lower(),
            "passwordHash": make_password(password),
            "phone": phone or "",
            "firstName": "",
            "lastName": "",
            "displayName": username,
            "bio": "",
            "avatarFileId": None,
            "isActive": True,
            "dateJoined": now,
            "createdAt": now,
            "updatedAt": now,
            "deletedAt": None,
        }
        try:
            result = UserService.collection().insert_one(doc)
        except DuplicateKeyError as exc:
            raise ValueError("User with this username or email already exists") from exc
        doc["_id"] = result.inserted_id
        return UserService.from_doc(doc)

    @staticmethod
    def authenticate(email: str, password: str) -> MongoUser | None:
        user = UserService.get_by_email(email)
        if not user or not user.check_password(password):
            return None
        return user

    @staticmethod
    def change_password(user_id: str, new_password: str):
        UserService.collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"passwordHash": make_password(new_password), "updatedAt": utcnow()}},
        )

    @staticmethod
    def get_or_create_user_from_yandex(yandex_data: dict):
        yandex_id = str(yandex_data.get("id"))
        collection = UserService.collection()

        user = UserService.from_doc(collection.find_one({"yandexId": yandex_id, "deletedAt": None}))
        if user:
            return user, False

        email = (yandex_data.get("default_email") or "").lower()
        if email:
            existing = collection.find_one({"email": email, "deletedAt": None})
            if existing:
                collection.update_one({"_id": existing["_id"]}, {"$set": {"yandexId": yandex_id, "updatedAt": utcnow()}})
                existing["yandexId"] = yandex_id
                return UserService.from_doc(existing), False

        now = utcnow()
        doc = {
            "username": yandex_data.get("login") or f"yandex_{yandex_id}",
            "email": email,
            "passwordHash": "",
            "firstName": yandex_data.get("first_name", ""),
            "lastName": yandex_data.get("last_name", ""),
            "displayName": yandex_data.get("real_name") or yandex_data.get("display_name") or yandex_data.get("login") or "",
            "bio": "",
            "avatarFileId": None,
            "yandexId": yandex_id,
            "isActive": True,
            "dateJoined": now,
            "createdAt": now,
            "updatedAt": now,
            "deletedAt": None,
        }
        result = collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return UserService.from_doc(doc), True

    @staticmethod
    def update_profile(
        user_id: str,
        *,
        display_name=None,
        bio=None,
        first_name=None,
        last_name=None,
        avatar_file_id=NOT_PROVIDED,
    ) -> MongoUser | None:
        updates = {"updatedAt": utcnow()}
        if display_name is not None:
            updates["displayName"] = display_name
        if bio is not None:
            updates["bio"] = bio
        if first_name is not None:
            updates["firstName"] = first_name
        if last_name is not None:
            updates["lastName"] = last_name
        if avatar_file_id is not NOT_PROVIDED:
            updates["avatarFileId"] = avatar_file_id

        UserService.collection().update_one(
            {"_id": ObjectId(user_id), "deletedAt": None},
            {"$set": updates},
        )
        return UserService.get_by_id(user_id)


class TokenService:
    ACCESS_LIFETIME_MINUTES = 15
    REFRESH_LIFETIME_DAYS = 7

    @staticmethod
    def collection():
        return mongo_service.db().tokens

    @staticmethod
    def build_access_jti_key(user_id: str, jti: str) -> str:
        return f"wp:auth:user:{user_id}:access:{jti}"

    @staticmethod
    def build_access_pattern(user_id: str) -> str:
        return f"wp:auth:user:{user_id}:access:*"

    @staticmethod
    def generate_access_token(user) -> tuple[str, str, datetime]:
        now = utcnow()
        exp = now + timedelta(minutes=TokenService.ACCESS_LIFETIME_MINUTES)
        jti = str(uuid.uuid4())
        payload = {
            "user_id": str(user.id),
            "username": user.username,
            "token_type": "access",
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256"), jti, exp

    @staticmethod
    def generate_refresh_token(user) -> tuple[str, datetime]:
        now = utcnow()
        exp = now + timedelta(days=TokenService.REFRESH_LIFETIME_DAYS)
        payload = {
            "user_id": str(user.id),
            "token_type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256"), exp

    @staticmethod
    def verify_token(token: str) -> dict | None:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def register_access_session(user_id: str, jti: str, ttl_seconds: int):
        cache_service.set(
            TokenService.build_access_jti_key(user_id, jti),
            {"status": "valid", "userId": str(user_id)},
            ttl=ttl_seconds,
        )

    @staticmethod
    def revoke_access_session(user_id: str, jti: str):
        cache_service.delete(TokenService.build_access_jti_key(user_id, jti))

    @staticmethod
    def revoke_all_access_sessions(user_id: str):
        cache_service.delByPattern(TokenService.build_access_pattern(user_id))

    @staticmethod
    def generate_tokens(user) -> dict:
        access_token, access_jti, access_exp = TokenService.generate_access_token(user)
        refresh_token, refresh_exp = TokenService.generate_refresh_token(user)
        now = utcnow()
        TokenService.collection().insert_many(
            [
                {
                    "userId": str(user.id),
                    "tokenType": "access",
                    "tokenHash": TokenService.hash_token(access_token),
                    "expiresAt": access_exp,
                    "isRevoked": False,
                    "createdAt": now,
                },
                {
                    "userId": str(user.id),
                    "tokenType": "refresh",
                    "tokenHash": TokenService.hash_token(refresh_token),
                    "expiresAt": refresh_exp,
                    "isRevoked": False,
                    "createdAt": now,
                },
            ]
        )
        ttl_seconds = max(1, int((access_exp - utcnow()).total_seconds()))
        TokenService.register_access_session(str(user.id), access_jti, ttl_seconds)
        return {"access_token": access_token, "refresh_token": refresh_token, "access_jti": access_jti}

    @staticmethod
    def is_token_revoked(token: str) -> bool:
        token_hash = TokenService.hash_token(token)
        token_doc = TokenService.collection().find_one({"tokenHash": token_hash})
        return not token_doc or token_doc.get("isRevoked", False)

    @staticmethod
    def revoke_token(token: str):
        TokenService.collection().update_one(
            {"tokenHash": TokenService.hash_token(token)},
            {"$set": {"isRevoked": True, "revokedAt": utcnow()}},
        )

    @staticmethod
    def revoke_all_user_tokens(user_id: str):
        TokenService.collection().update_many(
            {"userId": str(user_id), "isRevoked": False},
            {"$set": {"isRevoked": True, "revokedAt": utcnow()}},
        )

    @staticmethod
    def get_user_from_token(token: str):
        payload = TokenService.verify_token(token)
        if not payload:
            return None
        return UserService.get_by_id(payload.get("user_id"))
