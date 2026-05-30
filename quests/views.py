from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.cache import cache_service
from .exceptions import QuestConflictError, QuestNotFoundError
from .serializers import (
    ErrorResponseDTO,
    PaginationDTO,
    QuestCompleteResponseDTO,
    QuestCreateDTO,
    QuestDetailResponseDTO,
    QuestListResponseDTO,
    QuestResponseDTO,
    QuestStatisticsResponseDTO,
    QuestUpdateDTO,
)
from .services import QuestService


def quest_id_value(quest):
    return str(quest.get("_id") or quest.get("id"))


quest_error_400 = OpenApiResponse(response=ErrorResponseDTO, description="Ошибка валидации запроса.")
quest_error_401 = OpenApiResponse(response=ErrorResponseDTO, description="Требуется авторизация.")
quest_error_403 = OpenApiResponse(response=ErrorResponseDTO, description="Недостаточно прав на выполнение операции.")
quest_error_404 = OpenApiResponse(response=ErrorResponseDTO, description="Квест не найден.")
quest_error_409 = OpenApiResponse(response=ErrorResponseDTO, description="Конфликт бизнес-правил.")

quest_list_parameters = [
    OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, description="Номер страницы."),
    OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, description="Размер страницы."),
    OpenApiParameter(
        name="ordering",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Сортировка: created_at, -created_at, title, -title, difficulty, -difficulty, reward_gold, -reward_gold.",
    ),
    OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, description="Поиск по названию и описанию."),
    OpenApiParameter(name="status", type=str, location=OpenApiParameter.QUERY, description="Фильтр по статусу квеста."),
]


@extend_schema_view(
    get=extend_schema(
        tags=["Quests"],
        summary="Список квестов текущего пользователя",
        description="Возвращает квесты авторизованного пользователя с пагинацией, поиском и сортировкой.",
        parameters=quest_list_parameters,
        responses={
            200: OpenApiResponse(response=QuestListResponseDTO, description="Список квестов."),
            400: quest_error_400,
            401: quest_error_401,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
    post=extend_schema(
        tags=["Quests"],
        summary="Создать квест",
        description="Создает новый квест в статусе draft и привязывает его к текущему пользователю.",
        request=QuestCreateDTO,
        responses={
            201: OpenApiResponse(response=QuestDetailResponseDTO, description="Квест успешно создан."),
            400: quest_error_400,
            401: quest_error_401,
            409: quest_error_409,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
)
class QuestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pagination = PaginationDTO(data=request.query_params)
        pagination.is_valid(raise_exception=True)
        params = pagination.validated_data

        list_cache_key = QuestService.build_items_list_cache_key(
            user_id=request.user.id,
            page=params["page"],
            limit=params["limit"],
            ordering=params["ordering"],
            search=params.get("search", ""),
            status=params.get("status"),
        )

        cached = cache_service.get(list_cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        result = QuestService.get_quests_list(
            page=params["page"],
            limit=params["limit"],
            ordering=params["ordering"],
            search=params.get("search", ""),
            status=params.get("status"),
            owner=request.user,
        )

        payload = {
            "data": QuestResponseDTO(result["results"], many=True).data,
            "meta": {
                "total": result["count"],
                "page": result["page"],
                "limit": result["limit"],
                "totalPages": result["total_pages"],
                "hasNext": result["has_next"],
                "hasPrevious": result["has_previous"],
            },
        }
        cache_service.set(list_cache_key, payload, ttl=settings.CACHE_TTL_DEFAULT)
        return Response(payload, status=status.HTTP_200_OK)

    def post(self, request):
        dto = QuestCreateDTO(data=request.data)
        dto.is_valid(raise_exception=True)

        try:
            quest = QuestService.create_quest(dto.validated_data, owner=request.user)
        except QuestConflictError as exc:
            return Response(
                {"error": {"status": 409, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        return Response({"data": QuestResponseDTO(quest).data}, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=["Quests"],
        summary="Получить квест по ID",
        description="Возвращает один квест текущего пользователя.",
        responses={
            200: OpenApiResponse(response=QuestDetailResponseDTO, description="Квест найден."),
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
    put=extend_schema(
        tags=["Quests"],
        summary="Полностью обновить квест",
        description="Полное обновление всех обязательных полей квеста.",
        request=QuestUpdateDTO,
        responses={
            200: OpenApiResponse(response=QuestDetailResponseDTO, description="Квест обновлен."),
            400: quest_error_400,
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
            409: quest_error_409,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
    patch=extend_schema(
        tags=["Quests"],
        summary="Частично обновить квест",
        description="Частично обновляет переданные поля квеста.",
        request=QuestUpdateDTO,
        responses={
            200: OpenApiResponse(response=QuestDetailResponseDTO, description="Квест обновлен."),
            400: quest_error_400,
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
            409: quest_error_409,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
    delete=extend_schema(
        tags=["Quests"],
        summary="Удалить квест",
        description="Выполняет мягкое удаление квеста.",
        responses={
            204: OpenApiResponse(description="Квест удален."),
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
            409: quest_error_409,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    ),
)
class QuestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_owned_quest(self, request, quest_id):
        quest = QuestService.get_quest_by_id(quest_id)
        if (quest.get("owner") or {}).get("id") != str(request.user.id):
            return None
        return quest

    def get(self, request, quest_id):
        item_cache_key = QuestService.build_item_cache_key(request.user.id, quest_id)
        cached = cache_service.get(item_cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        try:
            quest = self._get_owned_quest(request, quest_id)
            if quest is None:
                return Response(
                    {"error": {"status": 403, "message": "Можно просматривать только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = {"data": QuestResponseDTO(quest).data}
        cache_service.set(item_cache_key, payload, ttl=settings.CACHE_TTL_DEFAULT)
        return Response(payload, status=status.HTTP_200_OK)

    def put(self, request, quest_id):
        try:
            quest = self._get_owned_quest(request, quest_id)
            if quest is None:
                return Response(
                    {"error": {"status": 403, "message": "Можно редактировать только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        dto = QuestUpdateDTO(data=request.data, context={"quest_id": quest_id})
        for field in dto.fields.values():
            field.required = True
        dto.is_valid(raise_exception=True)

        try:
            updated_quest = QuestService.update_quest(quest_id_value(quest), dto.validated_data)
        except QuestConflictError as exc:
            return Response(
                {"error": {"status": 409, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        return Response({"data": QuestResponseDTO(updated_quest).data}, status=status.HTTP_200_OK)

    def patch(self, request, quest_id):
        try:
            quest = self._get_owned_quest(request, quest_id)
            if quest is None:
                return Response(
                    {"error": {"status": 403, "message": "Можно редактировать только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        dto = QuestUpdateDTO(data=request.data, context={"quest_id": quest_id})
        dto.is_valid(raise_exception=True)
        if not dto.validated_data:
            return Response(
                {"error": {"status": 400, "message": "Не переданы данные"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated_quest = QuestService.update_quest(quest_id_value(quest), dto.validated_data)
        except QuestConflictError as exc:
            return Response(
                {"error": {"status": 409, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        return Response({"data": QuestResponseDTO(updated_quest).data}, status=status.HTTP_200_OK)

    def delete(self, request, quest_id):
        try:
            quest = self._get_owned_quest(request, quest_id)
            if quest is None:
                return Response(
                    {"error": {"status": 403, "message": "Можно удалять только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            QuestService.delete_quest(quest_id_value(quest))
            QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as exc:
            return Response(
                {"error": {"status": 409, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(
        tags=["Quests"],
        summary="Активировать квест",
        description="Переводит квест из draft в active.",
        request=None,
        responses={
            200: OpenApiResponse(response=QuestDetailResponseDTO, description="Квест активирован."),
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
            409: quest_error_409,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class QuestActivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quest_id):
        try:
            quest = QuestService.get_quest_by_id(quest_id)
            if (quest.get("owner") or {}).get("id") != str(request.user.id):
                return Response(
                    {"error": {"status": 403, "message": "Можно активировать только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            quest = QuestService.activate_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as exc:
            return Response(
                {"error": {"status": 409, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        return Response({"data": QuestResponseDTO(quest).data}, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=["Quests"],
        summary="Завершить квест",
        description="Завершает активный квест и возвращает рассчитанную награду.",
        request=None,
        responses={
            200: OpenApiResponse(response=QuestCompleteResponseDTO, description="Квест завершен."),
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
            409: quest_error_409,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class QuestCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quest_id):
        try:
            quest = QuestService.get_quest_by_id(quest_id)
            if (quest.get("owner") or {}).get("id") != str(request.user.id):
                return Response(
                    {"error": {"status": 403, "message": "Можно завершать только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            result = QuestService.complete_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as exc:
            return Response(
                {"error": {"status": 409, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        return Response(
            {
                "data": QuestResponseDTO(result["quest"]).data,
                "reward": result["reward"],
                "message": result["message"],
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    post=extend_schema(
        tags=["Quests"],
        summary="Восстановить удаленный квест",
        description="Восстанавливает ранее мягко удаленный квест.",
        request=None,
        responses={
            200: OpenApiResponse(response=QuestDetailResponseDTO, description="Квест восстановлен."),
            401: quest_error_401,
            403: quest_error_403,
            404: quest_error_404,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class QuestRestoreView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, quest_id):
        try:
            deleted_quest = QuestService.get_deleted_quest_by_id(quest_id)
            if (deleted_quest.get("owner") or {}).get("id") != str(request.user.id):
                return Response(
                    {"error": {"status": 403, "message": "Можно восстанавливать только свои квесты"}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            quest = QuestService.restore_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {"error": {"status": 404, "message": "Удаленный квест не найден"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        QuestService.invalidate_items_cache(request.user.id, item_id=quest_id_value(quest))
        return Response({"data": QuestResponseDTO(quest).data}, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["Quests"],
        summary="Статистика по квестам",
        description="Возвращает агрегированную статистику по квестам текущего пользователя.",
        responses={
            200: OpenApiResponse(response=QuestStatisticsResponseDTO, description="Статистика по квестам."),
            401: quest_error_401,
        },
        auth=[{"BearerAuth": []}, {"CookieAuth": []}],
    )
)
class QuestStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = QuestService.get_statistics(owner=request.user)
        return Response({"data": stats}, status=status.HTTP_200_OK)
