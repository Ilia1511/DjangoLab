import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret-key")
NODE_ENV = os.getenv("NODE_ENV", os.getenv("DJANGO_ENV", "development")).lower()
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_DEFAULT", "300"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin")
MONGO_DB_NAME = os.getenv("DB_NAME", "wp_labs")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_secure_password_change_in_prod")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "wp-labs-files")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "student")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "student_secure_rabbit_pass_change_in_prod")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "app.events")
RABBITMQ_DLX = os.getenv("RABBITMQ_DLX", "app.dlx")
QUEUE_USER_REGISTERED = os.getenv("QUEUE_USER_REGISTERED", "wp.auth.user.registered")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_SECURE = os.getenv("SMTP_SECURE", "true").lower() == "true"
DOCS_ENABLED = os.getenv(
    "SWAGGER_ENABLED",
    "true" if NODE_ENV != "production" else "false",
).lower() == "true"

YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
YANDEX_REDIRECT_URI = os.getenv(
    "YANDEX_REDIRECT_URI",
    "http://localhost:8000/api/auth/yandex/callback/",
)

ALLOWED_HOSTS = ["*"]
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = (
    "social_core.backends.yandex.YandexOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = NODE_ENV == "production"
CSRF_COOKIE_SECURE = NODE_ENV == "production"
SESSION_COOKIE_DOMAIN = None

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "social_django",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "quests",
    "users",
    "storage",
    'corsheaders',
]

default_renderers = ["rest_framework.renderers.JSONRenderer"]
if NODE_ENV != "production":
    default_renderers.append("rest_framework.renderers.BrowsableAPIRenderer")

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "quests.exception_handler.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": default_renderers,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "users.authentication.JWTCookieAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Lab Project API",
    "DESCRIPTION": "Документация API для лабораторных работ №2-№4",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api",
    "TAGS": [
        {"name": "Auth", "description": "Регистрация, вход, JWT в cookies и OAuth 2.0."},
        {"name": "Quests", "description": "CRUD-операции и бизнес-действия над квестами."},
        {"name": "Files", "description": "Загрузка, скачивание и удаление файлов через MinIO."},
        {"name": "Profile", "description": "Профиль текущего пользователя и привязка аватара."},
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [
        {"BearerAuth": []},
        {"CookieAuth": []},
    ],
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    },
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "Альтернативная схема авторизации для Swagger UI. "
                    "В реальном приложении access token обычно приходит из HttpOnly cookie."
                ),
            },
            "CookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "access_token",
                "description": (
                    "Авторизация через HttpOnly cookie `access_token`. "
                    "Если Swagger UI открыт на том же домене, браузер отправит cookie автоматически."
                ),
            },
            "YandexOAuth": {
                "type": "oauth2",
                "description": "Authorization Code Flow для входа через Яндекс OAuth 2.0.",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://oauth.yandex.ru/authorize",
                        "tokenUrl": "https://oauth.yandex.ru/token",
                        "scopes": {
                            "login:email": "Доступ к email пользователя",
                            "login:info": "Доступ к базовой информации профиля",
                        },
                    }
                },
            },
        }
    },
}

SPECTACULAR_SETTINGS["DESCRIPTION"] = "Документация API для лабораторных работ №2-№4"
SPECTACULAR_SETTINGS["TAGS"] = [
    {"name": "Auth", "description": "Регистрация, вход, JWT в cookies и OAuth 2.0."},
    {"name": "Quests", "description": "CRUD-операции и бизнес-действия над квестами."},
    {"name": "Files", "description": "Загрузка, скачивание и удаление файлов через MinIO."},
    {"name": "Profile", "description": "Профиль текущего пользователя и привязка аватара."},
]
SPECTACULAR_SETTINGS["COMPONENTS"]["securitySchemes"]["BearerAuth"]["description"] = (
    "Альтернативная схема авторизации для Swagger UI. "
    "В реальном приложении access token обычно приходит из HttpOnly cookie."
)
SPECTACULAR_SETTINGS["COMPONENTS"]["securitySchemes"]["CookieAuth"]["description"] = (
    "Авторизация через HttpOnly cookie `access_token`. "
    "Если Swagger UI открыт на том же домене, браузер отправит cookie автоматически."
)
SPECTACULAR_SETTINGS["COMPONENTS"]["securitySchemes"]["YandexOAuth"]["description"] = (
    "Authorization Code Flow для входа через Яндекс OAuth 2.0."
)
SPECTACULAR_SETTINGS["COMPONENTS"]["securitySchemes"]["YandexOAuth"]["flows"]["authorizationCode"]["scopes"] = {
    "login:email": "Доступ к email пользователя",
    "login:info": "Доступ к базовой информации профиля",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "sensitive_data": {
            "()": "WebApp.log_filters.SensitiveDataFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["sensitive_data"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "quests": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "users": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "storage": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "common.queue": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

MIDDLEWARE = [
        'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY", SECRET_KEY),
}

ROOT_URLCONF = "WebApp.urls"
WSGI_APPLICATION = "WebApp.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

LOGIN_REDIRECT_URL = "/dashboard/"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "django_internal.sqlite3",
    }
}

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_FILE_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = 0
