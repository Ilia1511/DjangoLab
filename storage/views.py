from urllib.parse import quote

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from users.serializers import ErrorResponseDTO
from .serializers import FileResponseDTO, FileUploadDTO
from .services import FileService, minio_storage_service


bad_request_response = OpenApiResponse(response=ErrorResponseDTO, description="Validation error.")
not_found_response = OpenApiResponse(response=ErrorResponseDTO, description="File not found.")
unauthorized_response = OpenApiResponse(response=ErrorResponseDTO, description="Unauthorized.")


def stream_minio_response(minio_response, chunk_size=8192):
    try:
        while True:
            chunk = minio_response.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        minio_response.close()
        minio_response.release_conn()


@extend_schema_view(
    post=extend_schema(
        tags=["Files"],
        summary="Upload file",
        request=FileUploadDTO,
        responses={201: FileResponseDTO, 400: bad_request_response, 401: unauthorized_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        dto = FileUploadDTO(data=request.data)
        dto.is_valid(raise_exception=True)
        try:
            doc = FileService.upload_file(dto.validated_data["file"], request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FileService.public_payload(doc), status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=["Files"],
        summary="Download file",
        responses={200: OpenApiResponse(description="Binary file stream."), 401: unauthorized_response, 404: not_found_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
    delete=extend_schema(
        tags=["Files"],
        summary="Delete file",
        responses={204: None, 401: unauthorized_response, 404: not_found_response},
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
)
class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        doc = FileService.get_file(str(file_id), user_id=request.user.id)
        if not doc:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        minio_response = minio_storage_service.get_file_stream(doc["objectKey"])
        response = StreamingHttpResponse(
            stream_minio_response(minio_response),
            content_type=doc["mimetype"],
            status=status.HTTP_200_OK,
        )
        filename = quote(doc["originalName"])
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        response["Content-Length"] = str(doc["size"])
        return response

    def delete(self, request, file_id):
        deleted = FileService.delete_file(str(file_id), request.user.id)
        if not deleted:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
