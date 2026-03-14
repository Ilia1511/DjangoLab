# quests/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class QuestQuerySet(models.QuerySet):

    def active(self):
        return self.filter(deleted_at__isnull=True)

    def delete(self, request, quest_id):
        try:
            QuestService.delete_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            import traceback
            print("=" * 50)
            print(f"DELETE ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            print("=" * 50)
            return Response(
                {
                    'error': {
                        'status': 500,
                        'message': str(e),
                        'type': type(e).__name__
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestManager(models.Manager):

    def get_queryset(self):
        return QuestQuerySet(self.model, using=self._db).active()

    def with_deleted(self):
        return QuestQuerySet(self.model, using=self._db)


class Quest(models.Model):

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quests',
        null=True,          # Временно, для старых записей
        blank=True,
        verbose_name='Владелец'
    )

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        ACTIVE = 'active', 'Активен'
        COMPLETED = 'completed', 'Завершён'
        FAILED = 'failed', 'Провален'

    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Лёгкий'
        MEDIUM = 'medium', 'Средний'
        HARD = 'hard', 'Сложный'
        LEGENDARY = 'legendary', 'Легендарный'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )

    title = models.CharField(
        max_length=200,
        verbose_name='Название квеста'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name='Статус'
    )
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
        verbose_name='Сложность'
    )
    reward_gold = models.PositiveIntegerField(
        default=0,
        verbose_name='Награда (золото)'
    )
    reward_experience = models.PositiveIntegerField(
        default=0,
        verbose_name='Награда (опыт)'
    )

    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    # Мягкое удаление
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Дата удаления'
    )

    # Менеджеры
    objects = QuestManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'quests'
        ordering = ['-created_at']
        verbose_name = 'Квест'
        verbose_name_plural = 'Квесты'

    def __str__(self):
        return self.title

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def activate(self):
        self.status = self.Status.ACTIVE
        self.save(update_fields=['status'])

    def complete(self):
        self.status = self.Status.COMPLETED
        self.save(update_fields=['status'])
