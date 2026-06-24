from django.urls import path
from .views import JoinCompetitionView, PredictMatchHTMXView


urlpatterns = [
    path('join/<str:code>/', JoinCompetitionView.as_view(), name='join_competition'),
    path('predict-htmx/<str:code>/', PredictMatchHTMXView.as_view(), name='predict_match_htmx'),
]