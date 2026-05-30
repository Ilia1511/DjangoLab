from django.urls import path

from . import views

urlpatterns = [
    path("quests/", views.QuestListCreateView.as_view()),
    path("quests/<str:quest_id>/", views.QuestDetailView.as_view()),
    path("quests/<str:quest_id>/activate/", views.QuestActivateView.as_view()),
    path("quests/<str:quest_id>/complete/", views.QuestCompleteView.as_view()),
    path("quests/<str:quest_id>/restore/", views.QuestRestoreView.as_view()),
    path("quests/statistics/", views.QuestStatisticsView.as_view()),
    path("items/", views.QuestListCreateView.as_view()),
    path("items/<str:quest_id>/", views.QuestDetailView.as_view()),
    path("items/<str:quest_id>/activate/", views.QuestActivateView.as_view()),
    path("items/<str:quest_id>/complete/", views.QuestCompleteView.as_view()),
    path("items/<str:quest_id>/restore/", views.QuestRestoreView.as_view()),
]
