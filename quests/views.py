# quests/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import QuestService

from .exceptions import QuestNotFoundError, QuestConflictError
from .serializers import (
    QuestCreateDTO,
    QuestUpdateDTO,
    QuestResponseDTO,
    PaginationDTO,
)



class QuestListCreateView(APIView):

    def get(self, request):
        pagination = PaginationDTO(data=request.query_params)
        pagination.is_valid(raise_exception=True)
        params = pagination.validated_data

        result = QuestService.get_quests_list(
            page=params['page'],
            limit=params['limit'],
            ordering=params['ordering'],
            search=params.get('search', ''),
            status=params.get('status'),
        )

        return Response({
            'data': QuestResponseDTO(result['results'], many=True).data,
            'meta': {
                'total': result['count'],
                'page': result['page'],
                'limit': result['limit'],
                'totalPages': result['total_pages'],
                'hasNext': result['has_next'],
                'hasPrevious': result['has_previous'],
            },
        }, status=status.HTTP_200_OK)

    def post(self, request):
        dto = QuestCreateDTO(data=request.data)
        dto.is_valid(raise_exception=True)

        quest = QuestService.create_quest(dto.validated_data)

        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_201_CREATED,
        )


class QuestDetailView(APIView):

    def get(self, request, quest_id):
        try:
            quest = QuestService.get_quest_by_id(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_200_OK,
        )

    def put(self, request, quest_id):
        try:
            QuestService.get_quest_by_id(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        dto = QuestUpdateDTO(
            data=request.data,
            context={'quest_id': quest_id},
        )
        for field in dto.fields.values():
            field.required = True
        dto.is_valid(raise_exception=True)

        try:
            quest = QuestService.update_quest(quest_id, dto.validated_data)
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_200_OK,
        )

    def patch(self, request, quest_id):
        try:
            QuestService.get_quest_by_id(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        dto = QuestUpdateDTO(
            data=request.data,
            context={'quest_id': quest_id},
        )
        dto.is_valid(raise_exception=True)

        if not dto.validated_data:
            return Response(
                {'error': {'status': 400, 'message': 'Не переданы данные для обновления'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quest = QuestService.update_quest(quest_id, dto.validated_data)
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, quest_id):
        try:
            QuestService.delete_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

class QuestActivateView(APIView):

    def post(self, request, quest_id):
        try:
            quest = QuestService.activate_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_200_OK,
        )


class QuestCompleteView(APIView):

    def post(self, request, quest_id):
        try:
            result = QuestService.complete_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'data': QuestResponseDTO(result['quest']).data,
            'reward': result['reward'],
            'message': result['message'],
        }, status=status.HTTP_200_OK)


class QuestRestoreView(APIView):

    def post(self, request, quest_id):
        try:
            quest = QuestService.restore_quest(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Удалённый квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_200_OK,
        )


class QuestStatisticsView(APIView):

    def get(self, request):
        stats = QuestService.get_statistics()
        return Response(
            {'data': stats},
            status=status.HTTP_200_OK,
        )