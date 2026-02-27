from django.urls import path

from . import views

urlpatterns = [
    path("", views.days_until_new_year, name="index"),
]