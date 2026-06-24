from django.urls import path
from .views import CompetitionListView, CompetitionDetailView

urlpatterns = [
    path('', CompetitionListView.as_view(), name='competition_list'),
    path('<str:code>/', CompetitionDetailView.as_view(), name='competition_detail')
]