# quests/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # CRUD эндпоинты
    path('quests/', views.QuestListCreateView.as_view()),
    path('quests/<uuid:quest_id>/', views.QuestDetailView.as_view()),

    # Бизнес-действия
    path('quests/<uuid:quest_id>/activate/', views.QuestActivateView.as_view()),
    path('quests/<uuid:quest_id>/complete/', views.QuestCompleteView.as_view()),
    path('quests/<uuid:quest_id>/restore/', views.QuestRestoreView.as_view()),

    # Статистика
    path('quests/statistics/', views.QuestStatisticsView.as_view()),
]