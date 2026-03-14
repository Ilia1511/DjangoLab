from django.conf import settings


def set_auth_cookies(response, access_token: str, refresh_token: str):
    """Установка токенов в cookies с флагами безопасности"""

    # Access token — короткий срок жизни
    response.set_cookie(
        key='access_token',
        value=access_token,
        max_age=15 * 60,  # 15 минут
        httponly=True,
        samesite='Lax',
        secure=False,  # True в продакшене
    )

    # Refresh token — длинный срок жизни
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        max_age=7 * 24 * 60 * 60,  # 7 дней
        httponly=True,
        samesite=None,
        secure=not settings.DEBUG,
    )

    return response


def clear_auth_cookies(response):
    """Удаление токенов из cookies (при logout)"""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response