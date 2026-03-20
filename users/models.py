from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import hashlib

class User(AbstractUser):

    yandex_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        verbose_name='Yandex ID'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Дата удаления'
    )

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])


class Token(models.Model):
    class TokenType(models.TextChoices):
        ACCESS = 'access', 'Access Token'
        REFRESH = 'refresh', 'Refresh Token'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tokens',
        verbose_name='Пользователь'
    )

    token_type = models.CharField(
        max_length=10,
        choices=TokenType.choices,
        verbose_name='Тип токена'
    )

    token_hash = models.CharField(
        max_length=64,
        verbose_name='Хеш токена'
    )

    expires_at = models.DateTimeField(
        verbose_name='Срок действия'
    )

    is_revoked = models.BooleanField(
        default=False,
        verbose_name='Отозван'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        db_table = 'tokens'
        verbose_name = 'Токен'
        verbose_name_plural = 'Токены'

    def __str__(self):
        return f'{self.token_type} - {self.user.username}'

    def revoke(self):
        self.is_revoked = True
        self.save(update_fields=['is_revoked'])

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()