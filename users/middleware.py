from django.contrib.auth.models import AnonymousUser
from .services import TokenService


class JWTAuthenticationMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return self.get_response(request)

        access_token = None

        # 1. Cookie
        access_token = request.COOKIES.get('access_token')

        # 2. Header
        if not access_token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header[7:]

        print(f"=== Token found: {access_token is not None} ===")

        if access_token:
            from .services import TokenService
            payload = TokenService.verify_token(access_token)
            print(f"=== Payload: {payload} ===")

            if payload and payload.get('token_type') == 'access':
                user = TokenService.get_user_from_token(access_token)
                print(f"=== User: {user} ===")

                if user and not user.deleted_at:
                    request.user = user
                    print(f"=== User set: {request.user} ===")

        return self.get_response(request)