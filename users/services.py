import jwt
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class TokenService:
    """Сервис для работы с JWT токенами"""

    @staticmethod
    def generate_access_token(user) -> str:
        """Генерация Access токена"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'token_type': 'access',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=15),
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        return token

    @staticmethod
    def generate_refresh_token(user) -> str:
        """Генерация Refresh токена"""
        payload = {
            'user_id': user.id,
            'token_type': 'refresh',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=7),
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        return token

    @staticmethod
    def verify_token(token: str) -> dict | None:
        """
        Проверка токена.
        Возвращает payload если токен валидный, иначе None.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            # Токен истёк
            return None
        except jwt.InvalidTokenError:
            # Невалидный токен
            return None

    @staticmethod
    def hash_token(token: str) -> str:
        """Хеширование токена для хранения в БД"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def generate_tokens(user) -> dict:
        access_token = TokenService.generate_access_token(user)
        refresh_token = TokenService.generate_refresh_token(user)

        from .models import Token
        from datetime import datetime, timedelta

        # Сохраняем хеши в БД
        Token.objects.create(
            user=user,
            token_type=Token.TokenType.ACCESS,
            token_hash=TokenService.hash_token(access_token),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )

        Token.objects.create(
            user=user,
            token_type=Token.TokenType.REFRESH,
            token_hash=TokenService.hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
        }

    @staticmethod
    def get_user_from_token(token: str):
        """Получение пользователя из токена"""
        payload = TokenService.verify_token(token)

        if not payload:
            return None

        try:
            user = User.objects.get(id=payload['user_id'])
            return user
        except User.DoesNotExist:
            return None



class UserService:
    """Сервис для работы с пользователями"""

    @staticmethod
    def get_or_create_user_from_yandex(yandex_data: dict):
        """
        Поиск или создание пользователя по данным от Яндекс.

        yandex_data содержит:
        - id: ID пользователя в Яндексе
        - login: логин
        - default_email: email
        - first_name, last_name: имя и фамилия
        """
        from .models import User

        yandex_id = str(yandex_data.get('id'))

        # Ищем пользователя по yandex_id
        try:
            user = User.objects.get(yandex_id=yandex_id)
            return user, False  # False = не создан, найден
        except User.DoesNotExist:
            pass

        # Ищем по email
        email = yandex_data.get('default_email')
        if email:
            try:
                user = User.objects.get(email=email)
                # Привязываем yandex_id к существующему пользователю
                user.yandex_id = yandex_id
                user.save(update_fields=['yandex_id'])
                return user, False
            except User.DoesNotExist:
                pass

        # Создаём нового пользователя
        username = yandex_data.get('login') or f'yandex_{yandex_id}'

        user = User.objects.create_user(
            username=username,
            email=email or '',
            first_name=yandex_data.get('first_name', ''),
            last_name=yandex_data.get('last_name', ''),
            yandex_id=yandex_id,
        )

        return user, True  # True = создан