import requests
import secrets
from urllib.parse import urlencode
from django.conf import settings


class YandexOAuth:
    """Сервис для OAuth 2.0 через Яндекс"""

    AUTHORIZE_URL = 'https://oauth.yandex.ru/authorize'
    TOKEN_URL = 'https://oauth.yandex.ru/token'
    USER_INFO_URL = 'https://login.yandex.ru/info'

    def __init__(self):
        self.client_id = settings.YANDEX_CLIENT_ID
        self.client_secret = settings.YANDEX_CLIENT_SECRET
        self.redirect_uri = settings.YANDEX_REDIRECT_URI

    def generate_state(self) -> str:
        """Генерация state для защиты от CSRF"""
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str) -> str:
        """Формирование ссылки для редиректа на Яндекс"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state,
        }
        return f'{self.AUTHORIZE_URL}?{urlencode(params)}'

    def exchange_code_for_token(self, code: str) -> dict | None:
        """Обмен кода авторизации на токен доступа"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        response = requests.post(self.TOKEN_URL, data=data)

        if response.status_code == 200:
            return response.json()
        return None

    def get_user_info(self, access_token: str) -> dict | None:
        """Получение данных пользователя от Яндекс"""
        headers = {
            'Authorization': f'OAuth {access_token}'
        }

        response = requests.get(self.USER_INFO_URL, headers=headers)

        if response.status_code == 200:
            return response.json()
        return None