from django.urls import path
from .views import JoinCompetitionView

urlpatterns = [
    path('join/<str:code>/', JoinCompetitionView.as_view(), name='join_competition'),
]