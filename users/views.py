from django.shortcuts import redirect
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import User, Token
from .oauth import YandexOAuth
from .services import TokenService, UserService
from .utils import set_auth_cookies, clear_auth_cookies
from .serializers import (
    UserRegistrationDTO,
    UserLoginDTO,
    UserResponseDTO,
    UserProfileDTO,
    ChangePasswordDTO,
)


# ==========================================
# Регистрация
# ==========================================

class RegisterView(APIView):
    """POST /auth/register - Регистрация нового пользователя"""
    permission_classes = [AllowAny]

    def post(self, request):
        dto = UserRegistrationDTO(data=request.data)
        dto.is_valid(raise_exception=True)

        data = dto.validated_data

        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
        )

        if data.get('phone'):
            user.phone = data['phone']
            user.save()

        tokens = TokenService.generate_tokens(user)

        response = Response(
            {
                'message': 'User registered successfully',
                'user': UserResponseDTO(user).data,
                'access_token': tokens['access_token'],
            },
            status=status.HTTP_201_CREATED
        )

        set_auth_cookies(
            response,
            tokens['access_token'],
            tokens['refresh_token']
        )

        return response


# ==========================================
# Вход
# ==========================================

class LoginView(APIView):
    """POST /auth/login - Вход пользователя"""
    permission_classes = [AllowAny]

    def post(self, request):
        dto = UserLoginDTO(data=request.data)
        dto.is_valid(raise_exception=True)

        data = dto.validated_data

        # Ищем пользователя по email
        try:
            user_obj = User.objects.get(email=data['email'])
            username = user_obj.username
        except User.DoesNotExist:
            return Response(
                {'error': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Аутентификация
        user = authenticate(username=username, password=data['password'])

        if not user:
            return Response(
                {'error': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.deleted_at:
            return Response(
                {'error': 'Аккаунт удалён'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        tokens = TokenService.generate_tokens(user)

        response = Response({
            'message': 'Login successful',
            'user': UserResponseDTO(user).data,
            'access_token': tokens['access_token'],
        })

        set_auth_cookies(
            response,
            tokens['access_token'],
            tokens['refresh_token']
        )

        return response


# ==========================================
# Обновление токенов
# ==========================================

class RefreshTokenView(APIView):
    """POST /auth/refresh - Обновление пары токенов"""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        payload = TokenService.verify_token(refresh_token)

        if not payload:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if payload.get('token_type') != 'refresh':
            return Response(
                {'error': 'Invalid token type'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = TokenService.get_user_from_token(refresh_token)

        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        tokens = TokenService.generate_tokens(user)

        response = Response({
            'message': 'Tokens refreshed successfully',
        })

        set_auth_cookies(
            response,
            tokens['access_token'],
            tokens['refresh_token']
        )

        return response


# ==========================================
# Проверка текущего пользователя
# ==========================================

class WhoAmIView(APIView):
    """GET /auth/whoami - Данные текущего пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'authenticated': True,
            'user': UserProfileDTO(request.user).data,
        })
# ==========================================
# Выход
# ==========================================

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response({
            'message': 'Logged out successfully',
        })

        clear_auth_cookies(response)

        return response


class LogoutAllView(APIView):
    """POST /auth/logout-all - Завершение всех сессий"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Отзываем все токены пользователя в БД
        Token.objects.filter(user=request.user, is_revoked=False).update(is_revoked=True)

        response = Response({
            'message': 'Logged out from all devices',
        })

        clear_auth_cookies(response)

        return response


# ==========================================
# OAuth Яндекс
# ==========================================

class YandexLoginView(APIView):
    """GET /auth/oauth/yandex - Инициация OAuth"""
    permission_classes = [AllowAny]

    def get(self, request):
        oauth = YandexOAuth()
        state = oauth.generate_state()
        request.session['oauth_state'] = state
        auth_url = oauth.get_authorization_url(state)
        return redirect(auth_url)


class YandexCallbackView(APIView):
    """GET /auth/oauth/yandex/callback - Обработка ответа OAuth"""
    permission_classes = [AllowAny]

    def get(self, request):
        oauth = YandexOAuth()

        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')

        if error:
            return Response(
                {'error': f'OAuth error: {error}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        saved_state = request.session.get('oauth_state')
        if not state or state != saved_state:
            return Response(
                {'error': 'Invalid state parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        del request.session['oauth_state']

        token_data = oauth.exchange_code_for_token(code)
        if not token_data:
            return Response(
                {'error': 'Failed to exchange code for token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        yandex_access_token = token_data.get('access_token')
        user_info = oauth.get_user_info(yandex_access_token)

        if not user_info:
            return Response(
                {'error': 'Failed to get user info'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, created = UserService.get_or_create_user_from_yandex(user_info)
        tokens = TokenService.generate_tokens(user)

        response = Response({
            'message': 'Successfully authenticated',
            'user': UserResponseDTO(user).data,
            'created': created,
        })

        set_auth_cookies(
            response,
            tokens['access_token'],
            tokens['refresh_token']
        )

        return response


# ==========================================
# Сброс пароля
# ==========================================

class ForgotPasswordView(APIView):
    """POST /auth/forgot-password - Запрос на сброс пароля"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Всегда возвращаем успех (безопасность - не раскрываем существование email)
        # В реальном приложении здесь отправка письма

        try:
            user = User.objects.get(email=email)
            # TODO: Генерация токена сброса и отправка email
            # reset_token = TokenService.generate_reset_token(user)
            # send_reset_email(user.email, reset_token)
        except User.DoesNotExist:
            pass

        return Response({
            'message': 'If the email exists, a reset link has been sent',
        })


class ResetPasswordView(APIView):
    """POST /auth/reset-password - Установка нового пароля"""
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        if not all([token, new_password, new_password_confirm]):
            return Response(
                {'error': 'Token, new_password and new_password_confirm are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != new_password_confirm:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: Проверка токена сброса
        # user = TokenService.verify_reset_token(token)
        # if not user:
        #     return Response({'error': 'Invalid or expired token'}, status=400)

        # user.set_password(new_password)
        # user.save()

        return Response({
            'message': 'Password has been reset successfully',
        })


# ==========================================
# Смена пароля (для авторизованных)
# ==========================================

class ChangePasswordView(APIView):
    """POST /auth/change-password - Смена пароля"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        dto = ChangePasswordDTO(data=request.data)
        dto.is_valid(raise_exception=True)

        data = dto.validated_data
        user = request.user

        if not user.check_password(data['old_password']):
            return Response(
                {'error': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(data['new_password'])
        user.save()

        # Отзываем все токены после смены пароля
        Token.objects.filter(user=user, is_revoked=False).update(is_revoked=True)

        # Выдаём новые токены
        tokens = TokenService.generate_tokens(user)

        response = Response({
            'message': 'Password changed successfully',
        })

        set_auth_cookies(
            response,
            tokens['access_token'],
            tokens['refresh_token']
        )

        return response



class QuestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Показываем только квесты текущего пользователя
        pagination = PaginationDTO(data=request.query_params)
        pagination.is_valid(raise_exception=True)
        params = pagination.validated_data

        result = QuestService.get_quests_list(
            page=params['page'],
            limit=params['limit'],
            ordering=params['ordering'],
            search=params.get('search', ''),
            status=params.get('status'),
            owner=request.user,  # Добавь это
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

        quest = QuestService.create_quest(
            dto.validated_data,
            owner=request.user,  # Добавь это
        )

        return Response(
            {'data': QuestResponseDTO(quest).data},
            status=status.HTTP_201_CREATED,
        )


class QuestDetailView(APIView):
    permission_classes = [IsAuthenticated]

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
            quest = QuestService.get_quest_by_id(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Проверка владения
        if quest.owner != request.user:
            return Response(
                {'error': {'status': 403, 'message': 'Можно редактировать только свои квесты'}},
                status=status.HTTP_403_FORBIDDEN,
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
            quest = QuestService.get_quest_by_id(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Проверка владения
        if quest.owner != request.user:
            return Response(
                {'error': {'status': 403, 'message': 'Можно редактировать только свои квесты'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        dto = QuestUpdateDTO(
            data=request.data,
            context={'quest_id': quest_id},
        )
        dto.is_valid(raise_exception=True)

        if not dto.validated_data:
            return Response(
                {'error': {'status': 400, 'message': 'Не переданы данные'}},
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
            quest = QuestService.get_quest_by_id(quest_id)
        except QuestNotFoundError:
            return Response(
                {'error': {'status': 404, 'message': 'Квест не найден'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Проверка владения
        if quest.owner != request.user:
            return Response(
                {'error': {'status': 403, 'message': 'Можно удалять только свои квесты'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            QuestService.delete_quest(quest_id)
        except QuestConflictError as e:
            return Response(
                {'error': {'status': 409, 'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)