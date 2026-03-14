from django.urls import path
from . import views

urlpatterns = [
    # Регистрация и вход
    path('auth/register/', views.RegisterView.as_view()),
    path('auth/login/', views.LoginView.as_view()),
    path('auth/refresh/', views.RefreshTokenView.as_view()),

    # Текущий пользователь
    path('auth/whoami/', views.WhoAmIView.as_view()),

    # Выход
    path('auth/logout/', views.LogoutView.as_view()),
    path('auth/logout-all/', views.LogoutAllView.as_view()),

    # OAuth
    path('auth/oauth/yandex/', views.YandexLoginView.as_view()),
    path('auth/oauth/yandex/callback/', views.YandexCallbackView.as_view()),

    # Сброс пароля
    path('auth/forgot-password/', views.ForgotPasswordView.as_view()),
    path('auth/reset-password/', views.ResetPasswordView.as_view()),

    # Смена пароля
    path('auth/change-password/', views.ChangePasswordView.as_view()),
]