from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        'access_token',
        access_token,
        max_age=60 * 15,        
        httponly=True,
        secure=settings.NODE_ENV == 'production',
        samesite='Lax',           
        path='/',                 
    )
    response.set_cookie(
        'refresh_token',
        refresh_token,
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        secure=settings.NODE_ENV == 'production',
        samesite='Lax',
        path='/',
    )


def clear_auth_cookies(response):
    response.delete_cookie('access_token',  path='/', samesite='Lax')
    response.delete_cookie('refresh_token', path='/', samesite='Lax')
