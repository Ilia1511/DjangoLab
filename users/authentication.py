from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from common.cache import cache_service
from .services import TokenService


class JWTCookieAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")
        auth_header = request.headers.get("Authorization", "")
        if not raw_token and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]
        if not raw_token:
            return None

        payload = TokenService.verify_token(raw_token)
        if not payload:
            raise AuthenticationFailed("Invalid or expired token")
        if payload.get("token_type") != "access":
            raise AuthenticationFailed("Invalid token type")
        if TokenService.is_token_revoked(raw_token):
            raise AuthenticationFailed("Token has been revoked")

        user_id = payload.get("user_id")
        jti = payload.get("jti")
        if not user_id or not jti:
            raise AuthenticationFailed("Token session id is missing")

        redis_exists = cache_service.exists(TokenService.build_access_jti_key(user_id, jti))
        if redis_exists is False:
            raise AuthenticationFailed("Token session is not active")

        user = TokenService.get_user_from_token(raw_token)
        if not user:
            raise AuthenticationFailed("User not found")
        if getattr(user, "deleted_at", None):
            raise AuthenticationFailed("User account is deleted")
        return user, raw_token
