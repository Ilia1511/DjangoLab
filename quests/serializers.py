# quests/serializers.py
from rest_framework import serializers
from .models import Quest


# ==========================================
# DTO для создания квеста
# ==========================================
class QuestCreateDTO(serializers.Serializer):
    """Валидация данных при создании квеста"""

    title = serializers.CharField(
        max_length=200,
        min_length=3,
        error_messages={
            'blank': 'Название не может быть пустым',
            'min_length': 'Минимум 3 символа',
        }
    )
    description = serializers.CharField(
        min_length=10,
        error_messages={
            'blank': 'Описание не может быть пустым',
            'min_length': 'Минимум 10 символов',
        }
    )
    status = serializers.ChoiceField(
        choices=Quest.Status.choices,
        default=Quest.Status.DRAFT,
    )
    difficulty = serializers.ChoiceField(
        choices=Quest.Difficulty.choices,
        default=Quest.Difficulty.EASY,
    )
    reward_gold = serializers.IntegerField(
        min_value=0,
        max_value=1000000,
        default=0,
        error_messages={
            'min_value': 'Награда не может быть отрицательной',
            'max_value': 'Максимум 1 000 000 золота',
        }
    )
    reward_experience = serializers.IntegerField(
        min_value=0,
        max_value=1000000,
        default=0,
    )

    def validate_title(self, value):
        """Дополнительная валидация названия"""
        if Quest.all_objects.filter(title=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('Квест с таким названием уже существует')
        return value


# ==========================================
# DTO для обновления квеста
# ==========================================
class QuestUpdateDTO(serializers.Serializer):
    """Валидация данных при обновлении квеста (все поля необязательные)"""

    title = serializers.CharField(
        max_length=200,
        min_length=3,
        required=False,
    )
    description = serializers.CharField(
        min_length=10,
        required=False,
    )
    status = serializers.ChoiceField(
        choices=Quest.Status.choices,
        required=False,
    )
    difficulty = serializers.ChoiceField(
        choices=Quest.Difficulty.choices,
        required=False,
    )
    reward_gold = serializers.IntegerField(
        min_value=0,
        max_value=1000000,
        required=False,
    )
    reward_experience = serializers.IntegerField(
        min_value=0,
        max_value=1000000,
        required=False,
    )

    def validate_title(self, value):
        """Проверка уникальности при обновлении"""
        quest_id = self.context.get('quest_id')
        if Quest.all_objects.filter(
            title=value,
            deleted_at__isnull=True
        ).exclude(id=quest_id).exists():
            raise serializers.ValidationError('Квест с таким названием уже существует')
        return value


# ==========================================
# DTO для пагинации
# ==========================================
class PaginationDTO(serializers.Serializer):
    """Валидация параметров пагинации"""

    page = serializers.IntegerField(
        min_value=1,
        default=1,
        error_messages={
            'min_value': 'Номер страницы должен быть >= 1',
            'invalid': 'Номер страницы должен быть числом',
        }
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=10,
        error_messages={
            'min_value': 'Лимит должен быть >= 1',
            'max_value': 'Лимит не может быть больше 100',
            'invalid': 'Лимит должен быть числом',
        }
    )
    ordering = serializers.ChoiceField(
        choices=[
            'created_at', '-created_at',
            'title', '-title',
            'difficulty', '-difficulty',
            'reward_gold', '-reward_gold',
        ],
        default='-created_at',
        required=False,
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    status = serializers.ChoiceField(
        choices=Quest.Status.choices,
        required=False,
        allow_blank=True,
    )


# ==========================================
# DTO для ответа (что отдаём клиенту)
# ==========================================
class QuestResponseDTO(serializers.ModelSerializer):
    """Сериализация квеста для ответа"""

    is_deleted = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quest
        fields = [
            'id',
            'title',
            'description',
            'status',
            'difficulty',
            'reward_gold',
            'reward_experience',
            'created_at',
            'updated_at',
            'is_deleted',
        ]


class PaginatedQuestResponseDTO(serializers.Serializer):
    """Ответ с пагинацией"""

    count = serializers.IntegerField()
    page = serializers.IntegerField()
    limit = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    results = QuestResponseDTO(many=True)

class QuestResponseDTO(serializers.ModelSerializer):
    is_deleted = serializers.BooleanField(read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True, default=None)

    class Meta:
        model = Quest
        fields = [
            'id',
            'title',
            'description',
            'status',
            'difficulty',
            'reward_gold',
            'reward_experience',
            'owner_username',
            'created_at',
            'updated_at',
            'is_deleted',
        ]