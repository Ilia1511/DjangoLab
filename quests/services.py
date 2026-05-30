import math
from datetime import datetime, timezone
from urllib.parse import quote_plus

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from common.cache import cache_service
from common.mongo import mongo_service
from .exceptions import QuestConflictError, QuestNotFoundError


def utcnow():
    return datetime.now(timezone.utc)


class QuestService:
    CACHE_LIST_PREFIX = "wp:items:user:{user_id}:list:"
    CACHE_ITEM_PREFIX = "wp:items:user:{user_id}:item:{item_id}"

    @staticmethod
    def collection():
        return mongo_service.db().quests

    @staticmethod
    def _safe_cache_part(value) -> str:
        if value is None:
            return "none"
        return quote_plus(str(value))

    @staticmethod
    def build_items_list_cache_key(user_id, page, limit, ordering, search, status) -> str:
        return (
            f"{QuestService.CACHE_LIST_PREFIX.format(user_id=user_id)}"
            f"page:{QuestService._safe_cache_part(page)}:"
            f"limit:{QuestService._safe_cache_part(limit)}:"
            f"ordering:{QuestService._safe_cache_part(ordering)}:"
            f"search:{QuestService._safe_cache_part(search)}:"
            f"status:{QuestService._safe_cache_part(status)}"
        )

    @staticmethod
    def build_items_list_pattern(user_id) -> str:
        return f"{QuestService.CACHE_LIST_PREFIX.format(user_id=user_id)}*"

    @staticmethod
    def build_item_cache_key(user_id, item_id) -> str:
        return QuestService.CACHE_ITEM_PREFIX.format(user_id=user_id, item_id=item_id)

    @staticmethod
    def invalidate_items_cache(user_id, item_id=None):
        cache_service.delByPattern(QuestService.build_items_list_pattern(user_id))
        if item_id is not None:
            cache_service.delete(QuestService.build_item_cache_key(user_id, item_id))

    @staticmethod
    def _object_id(quest_id):
        try:
            return ObjectId(str(quest_id))
        except Exception as exc:
            raise QuestNotFoundError("Quest not found") from exc

    @staticmethod
    def create_quest(data: dict, owner=None) -> dict:
        now = utcnow()
        doc = {
            "title": data["title"],
            "description": data["description"],
            "status": "draft",
            "difficulty": data.get("difficulty", "easy"),
            "reward_gold": data.get("reward_gold", 0),
            "reward_experience": data.get("reward_experience", 0),
            "owner": {
                "id": str(owner.id) if owner else None,
                "username": owner.username if owner else None,
            },
            "createdAt": now,
            "updatedAt": now,
            "deletedAt": None,
        }
        if doc["difficulty"] == "legendary":
            doc["reward_gold"] = max(doc["reward_gold"], 100)
            doc["reward_experience"] = max(doc["reward_experience"], 100)
        result = QuestService.collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def get_quest_by_id(quest_id) -> dict:
        doc = QuestService.collection().find_one({"_id": QuestService._object_id(quest_id), "deletedAt": None})
        if not doc:
            raise QuestNotFoundError("Quest not found")
        return doc

    @staticmethod
    def get_deleted_quest_by_id(quest_id) -> dict:
        doc = QuestService.collection().find_one({"_id": QuestService._object_id(quest_id), "deletedAt": {"$ne": None}})
        if not doc:
            raise QuestNotFoundError("Deleted quest not found")
        return doc

    @staticmethod
    def get_quests_list(page=1, limit=10, ordering="-created_at", search="", status=None, difficulty=None, owner=None) -> dict:
        query = {"deletedAt": None}
        if owner:
            query["owner.id"] = str(owner.id)
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]
        if status:
            query["status"] = status
        if difficulty:
            query["difficulty"] = difficulty

        field_map = {
            "created_at": "createdAt",
            "title": "title",
            "difficulty": "difficulty",
            "reward_gold": "reward_gold",
        }
        descending = ordering.startswith("-")
        sort_field = field_map.get(ordering.lstrip("-"), "createdAt")
        sort_dir = DESCENDING if descending else ASCENDING

        total_count = QuestService.collection().count_documents(query)
        total_pages = math.ceil(total_count / limit) if total_count else 1
        offset = (page - 1) * limit
        results = list(QuestService.collection().find(query).sort(sort_field, sort_dir).skip(offset).limit(limit))
        return {
            "results": results,
            "count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }

    @staticmethod
    def update_quest(quest_id, data: dict) -> dict:
        quest = QuestService.get_quest_by_id(quest_id)
        if quest.get("status") == "completed":
            raise QuestConflictError("Cannot edit completed quest")

        difficulty_order = {"easy": 1, "medium": 2, "hard": 3, "legendary": 4}
        if "difficulty" in data:
            if difficulty_order.get(data["difficulty"], 0) < difficulty_order.get(quest.get("difficulty"), 0):
                raise QuestConflictError("Cannot lower quest difficulty")

        allowed_fields = {"title", "description", "status", "difficulty", "reward_gold", "reward_experience"}
        update = {field: value for field, value in data.items() if field in allowed_fields}
        update["updatedAt"] = utcnow()
        QuestService.collection().update_one({"_id": quest["_id"]}, {"$set": update})
        quest.update(update)
        return quest

    @staticmethod
    def delete_quest(quest_id) -> bool:
        quest = QuestService.get_quest_by_id(quest_id)
        if quest.get("status") == "active":
            raise QuestConflictError("Cannot delete active quest")
        QuestService.collection().update_one({"_id": quest["_id"]}, {"$set": {"deletedAt": utcnow(), "updatedAt": utcnow()}})
        return True

    @staticmethod
    def restore_quest(quest_id) -> dict:
        quest = QuestService.get_deleted_quest_by_id(quest_id)
        update = {"deletedAt": None, "updatedAt": utcnow()}
        QuestService.collection().update_one({"_id": quest["_id"]}, {"$set": update})
        quest.update(update)
        return quest

    @staticmethod
    def activate_quest(quest_id) -> dict:
        quest = QuestService.get_quest_by_id(quest_id)
        if quest.get("status") != "draft":
            raise QuestConflictError("Only draft quest can be activated")
        return QuestService.update_quest(quest_id, {"status": "active"})

    @staticmethod
    def complete_quest(quest_id) -> dict:
        quest = QuestService.get_quest_by_id(quest_id)
        if quest.get("status") != "active":
            raise QuestConflictError("Only active quest can be completed")
        bonus = {"easy": 1.0, "medium": 1.5, "hard": 2.0, "legendary": 3.0}.get(quest.get("difficulty"), 1.0)
        total_gold = int(quest.get("reward_gold", 0) * bonus)
        total_experience = int(quest.get("reward_experience", 0) * bonus)
        quest = QuestService.update_quest(quest_id, {"status": "completed"})
        return {
            "quest": quest,
            "reward": {
                "base_gold": quest.get("reward_gold", 0),
                "base_experience": quest.get("reward_experience", 0),
                "difficulty_bonus": f"x{bonus}",
                "total_gold": total_gold,
                "total_experience": total_experience,
            },
            "message": f'Quest "{quest.get("title")}" completed!',
        }

    @staticmethod
    def get_statistics(owner=None) -> dict:
        query = {"deletedAt": None}
        if owner:
            query["owner.id"] = str(owner.id)
        quests = list(QuestService.collection().find(query))
        total = len(quests)
        total_gold = sum(q.get("reward_gold", 0) for q in quests)
        total_experience = sum(q.get("reward_experience", 0) for q in quests)
        by_status = {}
        by_difficulty = {}
        for quest in quests:
            by_status[quest.get("status")] = by_status.get(quest.get("status"), 0) + 1
            by_difficulty[quest.get("difficulty")] = by_difficulty.get(quest.get("difficulty"), 0) + 1
        return {
            "total_quests": total,
            "total_gold_pool": total_gold,
            "average_gold_reward": round(total_gold / total, 2) if total else 0,
            "total_experience_pool": total_experience,
            "by_status": by_status,
            "by_difficulty": by_difficulty,
        }
