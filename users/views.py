from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.cache import cache_service
from common.locks import distributed_lock
from common.queue import publish_user_registered
from .oauth import YandexOAuth
from .serializers import (
    AuthResponseDTO,
    AuthResponseWithAccessTokenDTO,
    ChangePasswordDTO,
    ErrorResponseDTO,
    ForgotPasswordRequestDTO,
    MessageResponseDTO,
    OAuthCallbackResponseDTO,
    OAuthLoginRedirectDTO,
    ProfileResponseDTO,
    ProfileUpdateDTO,
    RefreshResponseDTO,
    RefreshTokenRequestDTO,
    ResetPasswordRequestDTO,
    StructuredErrorResponseDTO,
    UserLoginDTO,
    UserProfileDTO,
    UserRegistrationDTO,
    UserResponseDTO,
    WhoAmIResponseDTO,
)
from .services import TokenService, UserService
from .utils import clear_auth_cookies, set_auth_cookies
from storage.services import FileService


unauthorized_response = OpenApiResponse(response=ErrorResponseDTO, description="Unauthorized.")
bad_request_response = OpenApiResponse(response=ErrorResponseDTO, description="Validation error.")


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Register user",
        request=UserRegistrationDTO,
        responses={201: AuthResponseWithAccessTokenDTO, 400: bad_request_response},
        auth=[],
    )
)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        dto = UserRegistrationDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data

        lock_key = f"lock:user:create:{data['email'].lower()}"
        lock_id = distributed_lock.acquire(lock_key, ttl_seconds=30)
        if lock_id is False:
            return Response({"error": "User registration is already in progress"}, status=status.HTTP_409_CONFLICT)

        try:
            user = UserService.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                phone=data.get("phone", ""),
            )
            publish_user_registered(user)
        finally:
            distributed_lock.release(lock_key, lock_id)

        tokens = TokenService.generate_tokens(user)
        response = Response(
            {
                "message": "User registered successfully",
                "user": UserResponseDTO(user).data,
                "access_token": tokens["access_token"],
            },
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return response


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Login",
        request=UserLoginDTO,
        responses={200: AuthResponseDTO, 400: bad_request_response, 401: unauthorized_response},
        auth=[],
    )
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        dto = UserLoginDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data

        user = UserService.authenticate(data["email"], data["password"])
        if not user:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = TokenService.generate_tokens(user)
        response = Response({"message": "Login successful", "user": UserResponseDTO(user).data})
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return response


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        request=RefreshTokenRequestDTO,
        responses={200: RefreshResponseDTO, 401: unauthorized_response},
        auth=[],
    )
)
class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token and request.data:
            refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token not found"}, status=status.HTTP_401_UNAUTHORIZED)

        payload = TokenService.verify_token(refresh_token)
        if not payload or payload.get("token_type") != "refresh" or TokenService.is_token_revoked(refresh_token):
            return Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        user = TokenService.get_user_from_token(refresh_token)
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_401_UNAUTHORIZED)

        TokenService.revoke_token(refresh_token)
        tokens = TokenService.generate_tokens(user)
        response = Response({"message": "Tokens refreshed successfully", "access_token": tokens["access_token"]})
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return response


@extend_schema_view(
    get=extend_schema(
        tags=["Auth"],
        summary="Current user profile",
        responses={200: WhoAmIResponseDTO, 401: unauthorized_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class WhoAmIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile_cache_key = f"wp:users:profile:{request.user.id}"
        cached_profile = cache_service.get(profile_cache_key)
        if cached_profile is not None:
            return Response(cached_profile)

        payload = {"authenticated": True, "user": UserProfileDTO(request.user).data}
        cache_service.set(profile_cache_key, payload)
        return Response(payload)


@extend_schema_view(
    get=extend_schema(
        tags=["Profile"],
        summary="Get current profile",
        responses={200: ProfileResponseDTO, 401: unauthorized_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
    post=extend_schema(
        tags=["Profile"],
        summary="Update current profile",
        request=ProfileUpdateDTO,
        responses={200: ProfileResponseDTO, 400: bad_request_response, 401: unauthorized_response, 404: bad_request_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
)
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ProfileResponseDTO(request.user).data)

    def post(self, request):
        dto = ProfileUpdateDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data

        avatar_file_id = data.get("avatarFileId")
        if avatar_file_id is not None and not FileService.user_owns_file(str(avatar_file_id), request.user.id):
            return Response({"error": "Avatar file not found or does not belong to current user"}, status=status.HTTP_404_NOT_FOUND)

        update_kwargs = {
            "display_name": data.get("displayName") if "displayName" in data else None,
            "bio": data.get("bio") if "bio" in data else None,
            "first_name": data.get("firstName") if "firstName" in data else None,
            "last_name": data.get("lastName") if "lastName" in data else None,
        }
        if "avatarFileId" in data:
            update_kwargs["avatar_file_id"] = str(avatar_file_id) if avatar_file_id is not None else None
            if request.user.avatar_file_id != update_kwargs["avatar_file_id"]:
                FileService.mark_usage(request.user.avatar_file_id, request.user.id, False)
                FileService.mark_usage(update_kwargs["avatar_file_id"], request.user.id, True)

        updated_user = UserService.update_profile(request.user.id, **update_kwargs)
        cache_service.delete(f"wp:users:profile:{request.user.id}")
        return Response(ProfileResponseDTO(updated_user).data)


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Logout from all devices",
        request=None,
        responses={200: MessageResponseDTO, 401: unauthorized_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        TokenService.revoke_all_user_tokens(request.user.id)
        TokenService.revoke_all_access_sessions(request.user.id)
        cache_service.delete(f"wp:users:profile:{request.user.id}")
        response = Response({"message": "Logged out from all devices"})
        clear_auth_cookies(response)
        return response


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Logout",
        request=None,
        responses={200: MessageResponseDTO, 401: unauthorized_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        access_token = request.COOKIES.get("access_token")
        auth_header = request.headers.get("Authorization", "")
        if not access_token and auth_header.startswith("Bearer "):
            access_token = auth_header[7:]

        if access_token:
            TokenService.revoke_token(access_token)
            payload = TokenService.verify_token(access_token)
            if payload and payload.get("jti") and payload.get("user_id"):
                TokenService.revoke_access_session(payload["user_id"], payload["jti"])

        cache_service.delete(f"wp:users:profile:{request.user.id}")
        response = Response({"message": "Logged out successfully"})
        clear_auth_cookies(response)
        return response


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema_view(
    get=extend_schema(tags=["Auth"], summary="Start Yandex OAuth", responses={302: OAuthLoginRedirectDTO}, auth=[{"YandexOAuth": []}])
)
class YandexLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        oauth = YandexOAuth()
        state = oauth.generate_state()
        request.session["oauth_state"] = state
        auth_url = oauth.get_authorization_url(state)
        return redirect(auth_url)


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema_view(
    get=extend_schema(
        tags=["Auth"],
        summary="Yandex OAuth callback",
        responses={200: OAuthCallbackResponseDTO, 400: bad_request_response},
        auth=[],
    )
)
class YandexCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication]
    authentication_classes = []

    def get(self, request):
        oauth = YandexOAuth()
        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")
        saved_state = request.session.get("oauth_state")

        if error:
            return Response({"error": f"OAuth error: {error}"}, status=status.HTTP_400_BAD_REQUEST)
        if not state or state != saved_state:
            return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)

        token_data = oauth.exchange_code_for_token(code)
        if not token_data:
            return Response({"error": "Failed to exchange code for token"}, status=status.HTTP_400_BAD_REQUEST)

        user_info = oauth.get_user_info(token_data.get("access_token"))
        if not user_info:
            return Response({"error": "Failed to get user info"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = UserService.get_or_create_user_from_yandex(user_info)
        tokens = TokenService.generate_tokens(user)
        response = Response({"message": "Successfully authenticated", "user": UserResponseDTO(user).data, "created": created})
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return response


@extend_schema_view(
    post=extend_schema(tags=["Auth"], summary="Forgot password", request=ForgotPasswordRequestDTO, responses={200: MessageResponseDTO, 400: bad_request_response}, auth=[])
)
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not request.data.get("email"):
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "If the email exists, a reset link has been sent"})


@extend_schema_view(
    post=extend_schema(tags=["Auth"], summary="Reset password", request=ResetPasswordRequestDTO, responses={200: MessageResponseDTO, 400: bad_request_response}, auth=[])
)
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        new_password_confirm = request.data.get("new_password_confirm")
        if not all([token, new_password, new_password_confirm]):
            return Response({"error": "Token, new_password and new_password_confirm are required"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != new_password_confirm:
            return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Password has been reset successfully"})


@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Change password",
        request=ChangePasswordDTO,
        responses={200: MessageResponseDTO, 400: StructuredErrorResponseDTO, 401: unauthorized_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        dto = ChangePasswordDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        data = dto.validated_data
        user = request.user
        if not user.check_password(data["old_password"]):
            return Response({"error": "Invalid current password"}, status=status.HTTP_400_BAD_REQUEST)

        UserService.change_password(user.id, data["new_password"])
        TokenService.revoke_all_user_tokens(user.id)
        TokenService.revoke_all_access_sessions(user.id)
        cache_service.delete(f"wp:users:profile:{user.id}")

        updated_user = UserService.get_by_id(user.id)
        tokens = TokenService.generate_tokens(updated_user)
        response = Response({"message": "Password changed successfully"})
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return response
