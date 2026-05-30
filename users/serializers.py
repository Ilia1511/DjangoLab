import re

from django.core.validators import RegexValidator
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from .services import UserService

phone_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{10,14}$",
    message="Enter a valid phone number, for example +79991234567.",
)


def validate_password_strength(password):
    errors = []
    if len(password) < 8:
        errors.append("Password must contain at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character.")
    if errors:
        raise serializers.ValidationError(errors)
    return password


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Registration",
            value={
                "username": "ivan_petrov",
                "email": "ivan@example.com",
                "password": "StrongPass1!",
                "password_confirm": "StrongPass1!",
                "phone": "+79991234567",
            },
        )
    ]
)
class UserRegistrationDTO(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, validators=[phone_validator])

    def validate_username(self, value):
        if UserService.username_exists(value):
            raise serializers.ValidationError("User with this username already exists.")
        return value

    def validate_email(self, value):
        email = value.lower()
        if UserService.email_exists(email):
            raise serializers.ValidationError("User with this email already exists.")
        return email

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data


class UserLoginDTO(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordDTO(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        if data["old_password"] == data["new_password"]:
            raise serializers.ValidationError({"new_password": "New password must differ from current password."})
        return data


class UserResponseDTO(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True, allow_blank=True)
    last_name = serializers.CharField(read_only=True, allow_blank=True)
    display_name = serializers.CharField(read_only=True, allow_blank=True)
    bio = serializers.CharField(read_only=True, allow_blank=True)
    avatar_file_id = serializers.UUIDField(read_only=True, allow_null=True)
    date_joined = serializers.CharField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)

    def to_representation(self, obj):
        return {
            "id": str(obj.id),
            "username": obj.username,
            "email": obj.email,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "display_name": obj.display_name,
            "bio": obj.bio,
            "avatar_file_id": obj.avatar_file_id,
            "date_joined": obj.date_joined.isoformat() if obj.date_joined else None,
            "is_active": obj.is_active,
        }


class UserProfileDTO(UserResponseDTO):
    has_yandex = serializers.BooleanField(read_only=True)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data.pop("is_active", None)
        data["has_yandex"] = bool(obj.yandex_id)
        return data


class AuthResponseDTO(serializers.Serializer):
    message = serializers.CharField()
    user = UserResponseDTO()


class AuthResponseWithAccessTokenDTO(serializers.Serializer):
    message = serializers.CharField()
    user = UserResponseDTO()
    access_token = serializers.CharField()


class RefreshTokenRequestDTO(serializers.Serializer):
    refresh_token = serializers.CharField(required=False)


class RefreshResponseDTO(serializers.Serializer):
    message = serializers.CharField()
    access_token = serializers.CharField()


class WhoAmIResponseDTO(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = UserProfileDTO()


class ProfileUpdateDTO(serializers.Serializer):
    displayName = serializers.CharField(required=False, allow_blank=True, max_length=80)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=500)
    firstName = serializers.CharField(required=False, allow_blank=True, max_length=80)
    lastName = serializers.CharField(required=False, allow_blank=True, max_length=80)
    avatarFileId = serializers.UUIDField(required=False, allow_null=True)
    avatar_file_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    fileId = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    def validate(self, data):
        avatar_values = [
            data.get("avatarFileId"),
            data.get("avatar_file_id"),
            data.get("fileId"),
        ]
        provided = [str(value) for value in avatar_values if value is not None]
        if len(set(provided)) > 1:
            raise serializers.ValidationError({"avatarFileId": "Use only one avatar file id value."})
        if provided:
            data["avatarFileId"] = provided[0]
        return data


class ProfileResponseDTO(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    displayName = serializers.CharField(read_only=True, allow_blank=True)
    bio = serializers.CharField(read_only=True, allow_blank=True)
    firstName = serializers.CharField(read_only=True, allow_blank=True)
    lastName = serializers.CharField(read_only=True, allow_blank=True)
    avatarFileId = serializers.UUIDField(read_only=True, allow_null=True)
    avatar_file_id = serializers.UUIDField(read_only=True, allow_null=True)
    avatarUrl = serializers.CharField(read_only=True, allow_null=True)

    def to_representation(self, obj):
        avatar_url = f"/api/files/{obj.avatar_file_id}/" if obj.avatar_file_id else None
        return {
            "id": str(obj.id),
            "username": obj.username,
            "email": obj.email,
            "displayName": obj.display_name,
            "bio": obj.bio,
            "firstName": obj.first_name,
            "lastName": obj.last_name,
            "avatarFileId": obj.avatar_file_id,
            "avatar_file_id": obj.avatar_file_id,
            "avatarUrl": avatar_url,
        }


class MessageResponseDTO(serializers.Serializer):
    message = serializers.CharField()


class OAuthLoginRedirectDTO(serializers.Serializer):
    detail = serializers.CharField(default="Browser redirects to OAuth provider.")


class OAuthCallbackResponseDTO(serializers.Serializer):
    message = serializers.CharField()
    user = UserResponseDTO()
    created = serializers.BooleanField()


class ForgotPasswordRequestDTO(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordRequestDTO(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)


class ErrorDetailDTO(serializers.Serializer):
    status = serializers.IntegerField()
    message = serializers.CharField()


class ErrorResponseDTO(serializers.Serializer):
    error = serializers.CharField()


class StructuredErrorResponseDTO(serializers.Serializer):
    error = ErrorDetailDTO()
