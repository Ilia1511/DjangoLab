from rest_framework.authentication import BaseAuthentication
from .services import TokenService


class JWTCookieAuthentication(BaseAuthentication):

    def authenticate(self, request):
        access_token = None

        # 1. Пробуем Cookie
        access_token = request.COOKIES.get('access_token')

        # 2. Пробуем Header
        if not access_token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header[7:]

        if not access_token:
            return None

        payload = TokenService.verify_token(access_token)

        if not payload or payload.get('token_type') != 'access':
            return None

        user = TokenService.get_user_from_token(access_token)

        if not user or user.deleted_at:
            return None

        return (user, access_token)