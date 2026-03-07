# quests/exception_handler.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Глобальный обработчик ошибок.
    Никогда не возвращает стек-трейсы пользователю.
    """

    # Сначала вызываем стандартный обработчик DRF
    response = exception_handler(exc, context)

    # Если DRF обработал (ValidationError, AuthError и т.д.)
    if response is not None:
        custom_response = {
            'error': {
                'status': response.status_code,
                'message': _get_error_message(response),
                'details': response.data,
            }
        }
        response.data = custom_response
        return response

    # Необработанные исключения — ловим сами
    # Логируем полный стек-трейс (для разработчиков)
    logger.error(f'Unhandled exception: {exc}', exc_info=True)

    # Возвращаем пользователю безопасное сообщение
    return Response(
        {
            'error': {
                'status': 500,
                'message': 'Внутренняя ошибка сервера',
                'details': None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_message(response):
    """Формирует человекочитаемое сообщение об ошибке"""
    status_messages = {
        400: 'Неверный формат данных',
        401: 'Не авторизован',
        403: 'Доступ запрещён',
        404: 'Ресурс не найден',
        405: 'Метод не разрешён',
        409: 'Конфликт данных',
        500: 'Внутренняя ошибка сервера',
    }
    return status_messages.get(response.status_code, 'Ошибка')