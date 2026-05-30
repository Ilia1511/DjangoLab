from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Upload avatar",
            value={"file": "<binary image file>"},
            request_only=True,
        )
    ]
)
class FileUploadDTO(serializers.Serializer):
    file = serializers.FileField(
        write_only=True,
        help_text="PNG/JPEG file. Maximum size is configured by MAX_FILE_SIZE.",
    )


class FileResponseDTO(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    userId = serializers.CharField(read_only=True)
    originalName = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)
    mimetype = serializers.CharField(read_only=True)
    isUsed = serializers.BooleanField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)
    updatedAt = serializers.DateTimeField(read_only=True)


class ProfileUpdateDTO(serializers.Serializer):
    displayName = serializers.CharField(required=False, allow_blank=True, max_length=80)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=500)
    firstName = serializers.CharField(required=False, allow_blank=True, max_length=80)
    lastName = serializers.CharField(required=False, allow_blank=True, max_length=80)
    avatarFileId = serializers.UUIDField(required=False, allow_null=True)


class ProfileResponseDTO(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    displayName = serializers.CharField(read_only=True, allow_blank=True)
    bio = serializers.CharField(read_only=True, allow_blank=True)
    firstName = serializers.CharField(read_only=True, allow_blank=True)
    lastName = serializers.CharField(read_only=True, allow_blank=True)
    avatarFileId = serializers.UUIDField(read_only=True, allow_null=True)

