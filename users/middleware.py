from django.utils.deprecation import MiddlewareMixin

from .services import TokenService


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        token = request.COOKIES.get("access_token")
        auth_header = request.headers.get("Authorization", "")
        if not token and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        if not token:
            return None

        if TokenService.is_token_revoked(token):
            request.user = None
            return None

        user = TokenService.get_user_from_token(token)
        if user:
            request.user = user
        return None
