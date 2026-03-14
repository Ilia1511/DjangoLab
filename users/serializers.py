from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
import re

from .models import User

# ==========================================
# Валидаторы
# ==========================================

phone_validator = RegexValidator(
    regex=r'^\+?[1-9]\d{10,14}$',
    message='Введите корректный номер телефона (например: +79991234567)'
)


def validate_password_strength(password):
    """Проверка сложности пароля"""
    errors = []

    if len(password) < 8:
        errors.append('Пароль должен содержать минимум 8 символов')

    if not re.search(r'[A-Z]', password):
        errors.append('Пароль должен содержать хотя бы одну заглавную букву')

    if not re.search(r'[a-z]', password):
        errors.append('Пароль должен содержать хотя бы одну строчную букву')

    if not re.search(r'\d', password):
        errors.append('Пароль должен содержать хотя бы одну цифру')

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Пароль должен содержать хотя бы один специальный символ')

    if errors:
        raise serializers.ValidationError(errors)

    return password


# ==========================================
# DTO для регистрации
# ==========================================

class UserRegistrationDTO(serializers.Serializer):
    """Валидация данных при регистрации"""

    username = serializers.CharField(
        min_length=3,
        max_length=30,
        error_messages={
            'min_length': 'Имя пользователя должно содержать минимум 3 символа',
            'max_length': 'Имя пользователя должно содержать максимум 30 символов',
        }
    )

    email = serializers.EmailField(
        error_messages={
            'invalid': 'Введите корректный email адрес'
        }
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            'min_length': 'Пароль должен содержать минимум 8 символов'
        }
    )

    password_confirm = serializers.CharField(write_only=True)

    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[phone_validator]
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Пользователь с таким именем уже существует')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value.lower()

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают'
            })
        return data


# ==========================================
# DTO для входа
# ==========================================

class UserLoginDTO(serializers.Serializer):
    """Валидация данных при входе"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


# ==========================================
# DTO для смены пароля
# ==========================================

class ChangePasswordDTO(serializers.Serializer):
    """Валидация данных при смене пароля"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Пароли не совпадают'
            })

        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                'new_password': 'Новый пароль должен отличаться от старого'
            })

        return data


# ==========================================
# DTO для ответа (БЕЗ чувствительных данных)
# ==========================================

class UserResponseDTO(serializers.ModelSerializer):
    """
    Сериализация пользователя для ответа.
    НЕ включает: password, yandex_id, токены
    """

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'is_active',
        ]
        read_only_fields = fields


class UserProfileDTO(serializers.ModelSerializer):
    """Расширенный профиль пользователя"""

    has_yandex = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'has_yandex',
        ]

    def get_has_yandex(self, obj):
        """Показываем только факт привязки, не сам ID"""
        return bool(obj.yandex_id)


# ==========================================
# DTO для обновления профиля
# ==========================================

class UserUpdateDTO(serializers.Serializer):
    """Валидация данных при обновлении профиля"""

    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[phone_validator]
    )


# ==========================================
# DTO для пагинации пользователей
# ==========================================

class UserPaginationDTO(serializers.Serializer):
    """Валидация параметров пагинации"""

    page = serializers.IntegerField(
        min_value=1,
        default=1,
        error_messages={
            'min_value': 'Номер страницы должен быть >= 1'
        }
    )

    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=10,
        error_messages={
            'min_value': 'Лимит должен быть >= 1',
            'max_value': 'Лимит не может быть больше 100'
        }
    )

    search = serializers.CharField(required=False, allow_blank=True, default='')


# ==========================================
# DTO для токенов (ответ)
# ==========================================

class TokenResponseDTO(serializers.Serializer):
    """
    Ответ с информацией о токенах.
    Сами токены передаются в cookies, не в теле!
    """

    message = serializers.CharField()
    expires_in = serializers.IntegerField(help_text='Время жизни access токена в секундах')


class AuthResponseDTO(serializers.Serializer):
    """Ответ после успешной авторизации"""

    message = serializers.CharField()
    user = UserResponseDTO()