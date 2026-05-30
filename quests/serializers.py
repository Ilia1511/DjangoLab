from rest_framework import serializers


QUEST_STATUSES = ("draft", "active", "completed", "failed")
QUEST_DIFFICULTIES = ("easy", "medium", "hard", "legendary")


class QuestCreateDTO(serializers.Serializer):
    title = serializers.CharField(max_length=200, min_length=3)
    description = serializers.CharField(min_length=10)
    status = serializers.ChoiceField(choices=QUEST_STATUSES, default="draft", required=False)
    difficulty = serializers.ChoiceField(choices=QUEST_DIFFICULTIES, default="easy")
    reward_gold = serializers.IntegerField(min_value=0, max_value=1000000, default=0)
    reward_experience = serializers.IntegerField(min_value=0, max_value=1000000, default=0)


class QuestUpdateDTO(serializers.Serializer):
    title = serializers.CharField(max_length=200, min_length=3, required=False)
    description = serializers.CharField(min_length=10, required=False)
    status = serializers.ChoiceField(choices=QUEST_STATUSES, required=False)
    difficulty = serializers.ChoiceField(choices=QUEST_DIFFICULTIES, required=False)
    reward_gold = serializers.IntegerField(min_value=0, max_value=1000000, required=False)
    reward_experience = serializers.IntegerField(min_value=0, max_value=1000000, required=False)


class PaginationDTO(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=10)
    ordering = serializers.ChoiceField(
        choices=[
            "created_at",
            "-created_at",
            "title",
            "-title",
            "difficulty",
            "-difficulty",
            "reward_gold",
            "-reward_gold",
        ],
        default="-created_at",
        required=False,
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(choices=QUEST_STATUSES, required=False, allow_blank=True)


class QuestResponseDTO(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    difficulty = serializers.CharField(read_only=True)
    reward_gold = serializers.IntegerField(read_only=True)
    reward_experience = serializers.IntegerField(read_only=True)
    owner_username = serializers.CharField(read_only=True, allow_blank=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)

    def to_representation(self, obj):
        return {
            "id": str(obj.get("_id") or obj.get("id")),
            "title": obj.get("title", ""),
            "description": obj.get("description", ""),
            "status": obj.get("status", ""),
            "difficulty": obj.get("difficulty", ""),
            "reward_gold": obj.get("reward_gold", 0),
            "reward_experience": obj.get("reward_experience", 0),
            "owner_username": (obj.get("owner") or {}).get("username"),
            "created_at": obj.get("createdAt").isoformat() if obj.get("createdAt") else None,
            "updated_at": obj.get("updatedAt").isoformat() if obj.get("updatedAt") else None,
            "is_deleted": obj.get("deletedAt") is not None,
        }


class QuestListMetaDTO(serializers.Serializer):
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    limit = serializers.IntegerField()
    totalPages = serializers.IntegerField()
    hasNext = serializers.BooleanField()
    hasPrevious = serializers.BooleanField()


class QuestListResponseDTO(serializers.Serializer):
    data = QuestResponseDTO(many=True)
    meta = QuestListMetaDTO()


class QuestDetailResponseDTO(serializers.Serializer):
    data = QuestResponseDTO()


class QuestCompleteResponseDTO(serializers.Serializer):
    data = QuestResponseDTO()
    reward = serializers.DictField()
    message = serializers.CharField()


class QuestStatisticsItemDTO(serializers.Serializer):
    total_quests = serializers.IntegerField()
    total_gold_pool = serializers.IntegerField()
    average_gold_reward = serializers.FloatField()
    total_experience_pool = serializers.IntegerField()
    by_status = serializers.DictField()
    by_difficulty = serializers.DictField()


class QuestStatisticsResponseDTO(serializers.Serializer):
    data = QuestStatisticsItemDTO()


class ErrorDetailDTO(serializers.Serializer):
    status = serializers.IntegerField()
    message = serializers.CharField()


class ErrorResponseDTO(serializers.Serializer):
    error = ErrorDetailDTO()
