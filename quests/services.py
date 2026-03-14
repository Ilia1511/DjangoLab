# quests/services.py
import math
from django.utils import timezone
from django.db.models import Q
from .models import Quest
from .exceptions import QuestNotFoundError, QuestConflictError, QuestValidationError


class QuestService:

    @staticmethod
    def create_quest(data: dict) -> Quest:
        data['status'] = Quest.Status.DRAFT

        if data.get('difficulty') == Quest.Difficulty.LEGENDARY:
            if data.get('reward_gold', 0) < 100:
                data['reward_gold'] = 100
            if data.get('reward_experience', 0) < 100:
                data['reward_experience'] = 100

        quest = Quest.objects.create(**data)
        return quest

    @staticmethod
    def get_quest_by_id(quest_id) -> Quest:
        try:
            return Quest.objects.get(id=quest_id)
        except Quest.DoesNotExist:
            raise QuestNotFoundError(f'Квест с ID {quest_id} не найден')

    @staticmethod
    def get_quests_list(
        page: int = 1,
        limit: int = 10,
        ordering: str = '-created_at',
        search: str = '',
        status: str = None,
        difficulty: str = None,
    ) -> dict:
        queryset = Quest.objects.all()

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        queryset = queryset.order_by(ordering)

        total_count = queryset.count()
        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

        offset = (page - 1) * limit
        quests = queryset[offset:offset + limit]

        return {
            'results': quests,
            'count': total_count,
            'page': page,
            'limit': limit,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }

    @staticmethod
    def update_quest(quest_id, data: dict) -> Quest:
        quest = QuestService.get_quest_by_id(quest_id)

        if quest.status == Quest.Status.COMPLETED:
            raise QuestConflictError('Нельзя редактировать завершённый квест')

        difficulty_order = {
            Quest.Difficulty.EASY: 1,
            Quest.Difficulty.MEDIUM: 2,
            Quest.Difficulty.HARD: 3,
            Quest.Difficulty.LEGENDARY: 4,
        }
        if 'difficulty' in data:
            current = difficulty_order.get(quest.difficulty, 0)
            new = difficulty_order.get(data['difficulty'], 0)
            if new < current:
                raise QuestConflictError('Нельзя понизить сложность квеста')

        for field, value in data.items():
            setattr(quest, field, value)
        quest.save()

        return quest

    @staticmethod
    def delete_quest(quest_id) -> bool:
        quest = QuestService.get_quest_by_id(quest_id)

        if quest.status == Quest.Status.ACTIVE:
            raise QuestConflictError(
                'Нельзя удалить активный квест. '
                'Сначала завершите или отмените его.'
            )

        quest.soft_delete()
        return True

    @staticmethod
    def restore_quest(quest_id) -> Quest:
        try:
            quest = Quest.all_objects.get(id=quest_id, deleted_at__isnull=False)
        except Quest.DoesNotExist:
            raise QuestNotFoundError('Удалённый квест не найден')

        quest.restore()
        return quest

    @staticmethod
    def activate_quest(quest_id) -> Quest:
        quest = QuestService.get_quest_by_id(quest_id)

        if quest.status != Quest.Status.DRAFT:
            raise QuestConflictError(
                f'Нельзя активировать квест в статусе "{quest.get_status_display()}"'
            )

        quest.status = Quest.Status.ACTIVE
        quest.save(update_fields=['status', 'updated_at'])
        return quest

    @staticmethod
    def complete_quest(quest_id) -> dict:
        quest = QuestService.get_quest_by_id(quest_id)

        if quest.status != Quest.Status.ACTIVE:
            raise QuestConflictError('Можно завершить только активный квест')

        difficulty_bonus = {
            Quest.Difficulty.EASY: 1.0,
            Quest.Difficulty.MEDIUM: 1.5,
            Quest.Difficulty.HARD: 2.0,
            Quest.Difficulty.LEGENDARY: 3.0,
        }
        bonus = difficulty_bonus.get(quest.difficulty, 1.0)

        total_gold = int(quest.reward_gold * bonus)
        total_experience = int(quest.reward_experience * bonus)

        quest.status = Quest.Status.COMPLETED
        quest.save(update_fields=['status', 'updated_at'])

        return {
            'quest': quest,
            'reward': {
                'base_gold': quest.reward_gold,
                'base_experience': quest.reward_experience,
                'difficulty_bonus': f'x{bonus}',
                'total_gold': total_gold,
                'total_experience': total_experience,
            },
            'message': f'Квест "{quest.title}" выполнен! '
                       f'Получено {total_gold} золота и {total_experience} опыта.',
        }

    @staticmethod
    def fail_quest(quest_id) -> Quest:
        quest = QuestService.get_quest_by_id(quest_id)

        if quest.status != Quest.Status.ACTIVE:
            raise QuestConflictError('Можно провалить только активный квест')

        quest.status = Quest.Status.FAILED
        quest.save(update_fields=['status', 'updated_at'])
        return quest

    @staticmethod
    def get_statistics() -> dict:
        from django.db.models import Count, Sum, Avg

        queryset = Quest.objects.all()

        stats = queryset.aggregate(
            total=Count('id'),
            total_gold=Sum('reward_gold'),
            avg_gold=Avg('reward_gold'),
            total_experience=Sum('reward_experience'),
        )

        by_status = dict(
            queryset.values_list('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        by_difficulty = dict(
            queryset.values_list('difficulty')
            .annotate(count=Count('id'))
            .values_list('difficulty', 'count')
        )

        return {
            'total_quests': stats['total'],
            'total_gold_pool': stats['total_gold'] or 0,
            'average_gold_reward': round(stats['avg_gold'] or 0, 2),
            'total_experience_pool': stats['total_experience'] or 0,
            'by_status': by_status,
            'by_difficulty': by_difficulty,
        }

    @staticmethod
    def create_quest(data: dict, owner=None) -> Quest:
        data['status'] = Quest.Status.DRAFT

        if owner:
            data['owner'] = owner

        if data.get('difficulty') == Quest.Difficulty.LEGENDARY:
            if data.get('reward_gold', 0) < 100:
                data['reward_gold'] = 100
            if data.get('reward_experience', 0) < 100:
                data['reward_experience'] = 100

        quest = Quest.objects.create(**data)
        return quest

    @staticmethod
    def get_quests_list(
            page: int = 1,
            limit: int = 10,
            ordering: str = '-created_at',
            search: str = '',
            status: str = None,
            difficulty: str = None,
            owner=None,  # Добавь параметр
    ) -> dict:
        queryset = Quest.objects.all()

        # Фильтр по владельцу
        if owner:
            queryset = queryset.filter(owner=owner)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )