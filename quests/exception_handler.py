# quests/exception_handler.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'error': {
                'status': response.status_code,
                'message': _get_error_message(response),
                'details': _sanitize_details(response.data),
            }
        }
        response.data = custom_response
        return response

    # Необработанные исключения
    logger.error(
        f'Unhandled exception in {context.get("view", "unknown")}: {type(exc).__name__}',
        exc_info=True
    )

    return Response(
        {
            'error': {
                'status': 500,
                'message': 'Internal server error',
                'details': None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_message(response):
    status_messages = {
        400: 'Bad request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not found',
        405: 'Method not allowed',
        409: 'Conflict',
        500: 'Internal server error',
    }
    return status_messages.get(response.status_code, 'Error')


def _sanitize_details(data):
    """Убираем чувствительные данные из ответа"""
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = {'password', 'token', 'secret', 'hash', 'salt'}
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                continue
            sanitized[key] = _sanitize_details(value)
        return sanitized
    return data